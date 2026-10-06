"""Almacenes independientes para el laboratorio HTTP, sin tocar candidaturas."""

import json
import secrets
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from nicrawl.applications import NotFound

SENDER_ID = 0x4E435453
RECEIVER_ID = 0x4E435452
SENDER_SCHEMA = (
    """CREATE TABLE trials(id TEXT PRIMARY KEY, draft_id TEXT NOT NULL,
    draft_version INTEGER NOT NULL, port INTEGER NOT NULL, receiver_id TEXT NOT NULL,
    payload TEXT NOT NULL, digest TEXT NOT NULL, state TEXT NOT NULL, scenario TEXT,
    receipt_id TEXT, message TEXT NOT NULL DEFAULT '',
    UNIQUE(draft_id,draft_version,receiver_id,port))""",
    """CREATE TABLE events(sequence INTEGER PRIMARY KEY, trial_id TEXT NOT NULL,
    at TEXT NOT NULL, action TEXT NOT NULL, state TEXT NOT NULL)""",
)
RECEIVER_SCHEMA = (
    "CREATE TABLE identity(id TEXT NOT NULL)",
    """CREATE TABLE requests(id TEXT PRIMARY KEY, digest TEXT NOT NULL,
    scenario TEXT NOT NULL)""",
    """CREATE TABLE receipts(id TEXT PRIMARY KEY, digest TEXT NOT NULL,
    receipt_id TEXT NOT NULL, result TEXT NOT NULL, payload TEXT NOT NULL)""",
)


def sender_path(database: Path) -> Path:
    return Path(str(database.resolve()) + ".http-trials.sqlite3")


def receiver_path(database: Path) -> Path:
    return Path(str(database.resolve()) + ".test-receiver.sqlite3")


def token_path(database: Path) -> Path:
    return Path(str(database.resolve()) + ".test-receiver.token")


def receiver_token(database: Path, *, create: bool = False) -> str:
    path = token_path(database)
    if path.is_symlink():
        raise ValueError("Ruta de token inválida.")
    if create:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("x", encoding="utf-8") as stream:
                stream.write(secrets.token_urlsafe(32))
        except FileExistsError:
            pass
    try:
        value = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as error:
        raise ValueError("Primero iniciá nicrawl test-receiver con la misma --db.") from error
    if not 32 <= len(value) <= 128 or not all(
        c.isascii() and (c.isalnum() or c in "-_") for c in value
    ):
        raise ValueError("Token de receptor inválido.")
    return value


@contextmanager
def connect(path: Path, identity: int, *, write: bool = False) -> Iterator[sqlite3.Connection]:
    if path.is_symlink():
        raise ValueError("Ruta de laboratorio inválida.")
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path.as_uri() + ("?mode=rwc" if write else "?mode=ro"), uri=True)
    con.row_factory = sqlite3.Row
    try:
        con.execute("BEGIN IMMEDIATE" if write else "BEGIN")
        actual = con.execute("PRAGMA application_id").fetchone()[0]
        version = con.execute("PRAGMA user_version").fetchone()[0]
        tables = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        if write and not tables and actual == 0 and version == 0:
            for sql in SENDER_SCHEMA if identity == SENDER_ID else RECEIVER_SCHEMA:
                con.execute(sql)
            if identity == RECEIVER_ID:
                con.execute("INSERT INTO identity VALUES(?)", (secrets.token_hex(16),))
            con.execute(f"PRAGMA application_id={identity}")
            con.execute("PRAGMA user_version=1")
        elif actual != identity or version != 1:
            raise ValueError("Archivo ajeno o incompatible con este laboratorio.")
        yield con
        if write:
            con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()


def row(con: sqlite3.Connection, identifier: str) -> sqlite3.Row:
    result = con.execute("SELECT * FROM trials WHERE id=?", (identifier,)).fetchone()
    if result is None:
        raise NotFound("Ensayo HTTP no encontrado.")
    return cast(sqlite3.Row, result)


def event(
    con: sqlite3.Connection, identifier: str, action: str, state: str, message: str = ""
) -> None:
    con.execute("UPDATE trials SET state=?,message=? WHERE id=?", (state, message, identifier))
    con.execute(
        "INSERT INTO events(trial_id,at,action,state) VALUES(?,?,?,?)",
        (identifier, datetime.now(UTC).isoformat(), action, state),
    )


def report(con: sqlite3.Connection, identifier: str) -> dict[str, Any]:
    item = row(con, identifier)
    return {
        "simulation": True,
        "transport": "http-loopback",
        "id": identifier,
        "destination": f"http://127.0.0.1:{item['port']}",
        "receiver_id": item["receiver_id"],
        "review_sha256": item["digest"],
        "state": item["state"],
        "message": item["message"],
        "receipt_id": item["receipt_id"],
        "payload": json.loads(item["payload"]),
        "history": [
            dict(e)
            for e in con.execute(
                "SELECT at,action,state FROM events WHERE trial_id=? ORDER BY sequence",
                (identifier,),
            )
        ],
    }
