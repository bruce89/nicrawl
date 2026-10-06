"""Receptor de ensayo durable: no abre sockets ni modifica candidaturas reales."""

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast
from uuid import uuid4

from nicrawl import applications

Scenario = Literal["accepted", "rejected", "timeout-before", "timeout-after"]
SCENARIOS = ("accepted", "rejected", "timeout-before", "timeout-after")
DESTINATION = "local://nicrawl-test-receiver"
APP_ID = 0x4E43534D


def store_path(database: Path) -> Path:
    return Path(str(database.resolve()) + ".simulation.sqlite3")


@contextmanager
def _store(database: Path, *, write: bool = False) -> Iterator[sqlite3.Connection]:
    path = store_path(database)
    if path.is_symlink() or (path.exists() and database.exists() and path.samefile(database)):
        raise ValueError("Ruta de simulación inválida.")
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path.as_uri() + ("?mode=rwc" if write else "?mode=ro"), uri=True)
    con.row_factory = sqlite3.Row
    try:
        con.execute("BEGIN IMMEDIATE" if write else "BEGIN")
        identity = con.execute("PRAGMA application_id").fetchone()[0]
        version = con.execute("PRAGMA user_version").fetchone()[0]
        tables = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        if write and not tables and identity == 0 and version == 0:
            con.execute("""CREATE TABLE submissions(
                id TEXT PRIMARY KEY, draft_id TEXT NOT NULL, draft_version INTEGER NOT NULL,
                payload TEXT NOT NULL, digest TEXT NOT NULL, state TEXT NOT NULL,
                created_at TEXT NOT NULL, UNIQUE(draft_id,draft_version))""")
            con.execute("""CREATE TABLE receipts(
                submission_id TEXT PRIMARY KEY, digest TEXT NOT NULL,
                receipt_id TEXT NOT NULL, result TEXT NOT NULL)""")
            con.execute("""CREATE TABLE events(
                sequence INTEGER PRIMARY KEY, submission_id TEXT NOT NULL,
                at TEXT NOT NULL, action TEXT NOT NULL, state TEXT NOT NULL)""")
            con.execute(f"PRAGMA application_id={APP_ID}")
            con.execute("PRAGMA user_version=1")
        elif identity != APP_ID or version != 1:
            raise ValueError("Base de simulación ajena o incompatible.")
        yield con
        if write:
            con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()


def _event(con: sqlite3.Connection, identifier: str, action: str, state: str) -> None:
    con.execute("UPDATE submissions SET state=? WHERE id=?", (state, identifier))
    con.execute(
        "INSERT INTO events(submission_id,at,action,state) VALUES(?,?,?,?)",
        (identifier, datetime.now(UTC).isoformat(), action, state),
    )


def _row(con: sqlite3.Connection, identifier: str) -> sqlite3.Row:
    row = con.execute("SELECT * FROM submissions WHERE id=?", (identifier,)).fetchone()
    if row is None:
        raise applications.NotFound("Simulación no encontrada.")
    return cast(sqlite3.Row, row)


def _report(con: sqlite3.Connection, identifier: str) -> dict[str, Any]:
    row = _row(con, identifier)
    receipt = con.execute("SELECT * FROM receipts WHERE submission_id=?", (identifier,)).fetchone()
    # El emisor no conoce el recibo hasta recibir respuesta o reconciliar.
    return {
        "simulation": True,
        "destination": DESTINATION,
        "id": identifier,
        "state": row["state"],
        "review_sha256": row["digest"],
        "payload": json.loads(row["payload"]),
        "receipt_id": receipt["receipt_id"] if receipt and row["state"] != "uncertain" else None,
        "history": [
            dict(item)
            for item in con.execute(
                "SELECT at,action,state FROM events WHERE submission_id=? ORDER BY sequence",
                (identifier,),
            )
        ],
    }


def prepare(database: Path, draft_id: str, version: int) -> dict[str, Any]:
    if type(version) is not int or version < 1:
        raise ValueError("La versión debe ser un entero positivo.")
    draft = applications.show_draft(database, draft_id, version)
    if draft["questions"]:
        raise ValueError(
            "Resolvé las preguntas pendientes y guardá una nueva revisión antes del ensayo."
        )
    payload = {
        key: draft[key] for key in ("id", "application_id", "version", "profile_version", "preview")
    }
    payload["destination"] = DESTINATION
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    with _store(database, write=True) as con:
        existing = con.execute(
            "SELECT id,digest FROM submissions WHERE draft_id=? AND draft_version=?",
            (draft_id, version),
        ).fetchone()
        if existing:
            if existing["digest"] != digest:
                raise applications.Conflict("Cambió el contenido de una versión ya preparada.")
            return _report(con, existing["id"])
        identifier = str(uuid4())
        con.execute(
            "INSERT INTO submissions VALUES(?,?,?,?,?,'prepared',?)",
            (identifier, draft_id, version, raw, digest, datetime.now(UTC).isoformat()),
        )
        _event(con, identifier, "prepared", "prepared")
        return _report(con, identifier)


def show(database: Path, identifier: str) -> dict[str, Any]:
    if not store_path(database).exists():
        raise applications.NotFound("Simulación no encontrada.")
    with _store(database) as con:
        return _report(con, identifier)


def send(
    database: Path, identifier: str, review_sha256: str, scenario: str = "accepted"
) -> dict[str, Any]:
    if scenario not in SCENARIOS:
        raise ValueError("Escenario de ensayo desconocido.")
    if not store_path(database).exists():
        raise applications.NotFound("Simulación no encontrada.")
    with _store(database, write=True) as con:
        row = _row(con, identifier)
        if review_sha256 != row["digest"]:
            raise applications.Conflict("La confirmación no coincide con el contenido preparado.")
        if row["state"] == "uncertain":
            raise applications.Conflict("Resultado incierto: reconciliá antes de volver a enviar.")
        if row["state"] in {"accepted", "rejected"}:
            return _report(con, identifier)
        # Ensayo determinista, una transacción local serializa recepción y resultado.
        # No representa una transacción distribuida ni una llamada HTTP real.
        if scenario != "timeout-before":
            result = "rejected" if scenario == "rejected" else "accepted"
            con.execute(
                "INSERT INTO receipts VALUES(?,?,?,?)",
                (identifier, row["digest"], str(uuid4()), result),
            )
        state = "uncertain" if scenario.startswith("timeout-") else scenario
        _event(con, identifier, f"send:{scenario}", state)
        return _report(con, identifier)


def reconcile(database: Path, identifier: str) -> dict[str, Any]:
    if not store_path(database).exists():
        raise applications.NotFound("Simulación no encontrada.")
    with _store(database, write=True) as con:
        row = _row(con, identifier)
        if row["state"] != "uncertain":
            return _report(con, identifier)
        receipt = con.execute(
            "SELECT result FROM receipts WHERE submission_id=?", (identifier,)
        ).fetchone()
        # Ausencia es definitiva SOLO en este receptor local sin solicitudes en vuelo.
        state = receipt["result"] if receipt else "prepared"
        _event(con, identifier, "reconcile:found" if receipt else "reconcile:absent", state)
        return _report(con, identifier)
