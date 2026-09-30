"""SQLite: intentos durables separados de la publicación atómica del lote."""

import json
import sqlite3
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote, unquote
from uuid import uuid4

from nicrawl.domain import content_hash, material_json
from nicrawl.sources.remotive import ADAPTER_VERSION, NORMALIZER_VERSION, SCOPE, SOURCE, SourceBatch

APPLICATION_ID = 0x4E494352
SCHEMA_VERSION = 2

PERSONAL_SCHEMA = """CREATE TABLE personal_state(job_key TEXT PRIMARY KEY REFERENCES jobs(job_key),
        state TEXT NOT NULL CHECK(state IN ('favorite','dismissed','unreviewed')),
        note TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL)"""

SCHEMA = (
    "CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)",
    """CREATE TABLE runs(
        run_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, scope TEXT NOT NULL,
        adapter_version TEXT NOT NULL, normalizer_version TEXT NOT NULL,
        started_at TEXT NOT NULL, finished_at TEXT, status TEXT NOT NULL,
        coverage TEXT NOT NULL DEFAULT 'incomplete', message TEXT,
        metrics TEXT NOT NULL DEFAULT '{}')""",
    """CREATE TABLE source_state(source_id TEXT PRIMARY KEY, next_allowed_at TEXT,
        last_attempt_at TEXT, disabled_reason TEXT)""",
    """CREATE TABLE attempts(id INTEGER PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(run_id),
        source_id TEXT NOT NULL, attempted_at TEXT NOT NULL)""",
    "CREATE INDEX attempts_source_time ON attempts(source_id, attempted_at)",
    """CREATE TABLE jobs(job_key TEXT PRIMARY KEY, source_id TEXT NOT NULL,
        source_job_id TEXT NOT NULL, source_url TEXT NOT NULL, payload TEXT NOT NULL,
        content_hash TEXT NOT NULL, normalizer_version TEXT NOT NULL,
        first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL, last_changed_at TEXT NOT NULL,
        UNIQUE(source_id, source_job_id))""",
    """CREATE TABLE run_items(run_id TEXT NOT NULL REFERENCES runs(run_id),
        job_key TEXT NOT NULL REFERENCES jobs(job_key), kind TEXT NOT NULL,
        PRIMARY KEY(run_id, job_key))""",
    """CREATE TABLE changes(id INTEGER PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(run_id),
        job_key TEXT NOT NULL REFERENCES jobs(job_key), kind TEXT NOT NULL,
        before_json TEXT, after_json TEXT NOT NULL)""",
    PERSONAL_SCHEMA,
)


class StorageError(RuntimeError):
    pass


class Deferred(RuntimeError):
    pass


def missing_job(connection: sqlite3.Connection, job_key: str) -> StorageError:
    """Sugerir claves existentes con el mismo ID, sin interpretar alias como identidad."""
    source_job_id = unquote(job_key.rsplit(":", 1)[-1])
    rows = connection.execute(
        "SELECT job_key FROM jobs WHERE source_job_id=? ORDER BY job_key LIMIT 4",
        (source_job_id,),
    ).fetchall()
    suggestions = [row["job_key"] for row in rows if row["job_key"] != job_key]
    message = f"Oferta no encontrada: {job_key}"
    if suggestions:
        message += ". ¿Quisiste usar " + ", ".join(suggestions[:3]) + "?"
    return StorageError(message)


class Repository:
    def __init__(self, path: Path, *, readonly: bool = False) -> None:
        self.path = path.resolve()
        if readonly and not self.path.is_file():
            raise StorageError("No hay base local. Ejecutá collect primero.")
        self.connection = sqlite3.connect(
            self.path.as_uri() + ("?mode=ro" if readonly else "?mode=rwc"),
            uri=True,
            timeout=2,
        )
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        try:
            app_id = self.connection.execute("PRAGMA application_id").fetchone()[0]
            version = self.connection.execute("PRAGMA user_version").fetchone()[0]
            tables = self.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            if not tables and app_id == 0 and version == 0 and not readonly:
                with self.connection:
                    # DDL también debe comenzar dentro de una transacción explícita.
                    self.connection.execute("BEGIN IMMEDIATE")
                    for statement in SCHEMA:
                        self.connection.execute(statement)
                    self.connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
                    self.connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
                    self.connection.execute(
                        "INSERT INTO schema_migrations VALUES(?,"
                        "strftime('%Y-%m-%dT%H:%M:%SZ','now'))",
                        (SCHEMA_VERSION,),
                    )
            elif app_id == APPLICATION_ID and version == 1:
                if readonly:
                    raise StorageError(
                        "Base de esquema 1: respaldala y abrila para escritura con "
                        "nicrawl 0.6.0 para migrar a esquema 2."
                    )
                with self.connection:
                    self.connection.execute("BEGIN IMMEDIATE")
                    current = self.connection.execute("PRAGMA user_version").fetchone()[0]
                    if current == 1:
                        self.connection.execute(PERSONAL_SCHEMA)
                        self.connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
                        self.connection.execute(
                            "INSERT INTO schema_migrations VALUES(?,"
                            "strftime('%Y-%m-%dT%H:%M:%SZ','now'))",
                            (SCHEMA_VERSION,),
                        )
                    elif current != SCHEMA_VERSION:
                        raise StorageError("La versión de esquema cambió durante la migración.")
            elif app_id != APPLICATION_ID or version != SCHEMA_VERSION:
                raise StorageError("Base ajena o versión de esquema no compatible; no se modificó.")
        except BaseException:
            self.connection.close()
            raise

    def close(self) -> None:
        self.connection.close()

    def start_run(
        self,
        now: datetime,
        *,
        source: str = SOURCE,
        scope: str = SCOPE,
        adapter_version: str = ADAPTER_VERSION,
    ) -> str:
        run_id = str(uuid4())
        with self.connection:
            self.connection.execute(
                "UPDATE runs SET status='interrupted', finished_at=?, message=? "
                "WHERE status='running' AND source_id=?",
                (now.isoformat(), "Recuperado tras interrupción del proceso.", source),
            )
            self.connection.execute(
                "INSERT INTO runs(run_id,source_id,scope,adapter_version,normalizer_version,"
                "started_at,status) VALUES(?,?,?,?,?,?,'running')",
                (run_id, source, scope, adapter_version, NORMALIZER_VERSION, now.isoformat()),
            )
            self.connection.execute(
                "INSERT OR IGNORE INTO source_state(source_id) VALUES(?)", (source,)
            )
        return run_id

    def gate(self, now: datetime, *, source: str = SOURCE) -> None:
        row = self.connection.execute(
            "SELECT * FROM source_state WHERE source_id=?", (source,)
        ).fetchone()
        if row and row["disabled_reason"]:
            raise StorageError(f"Fuente detenida para revisión: {row['disabled_reason']}")
        if row and row["last_attempt_at"] and datetime.fromisoformat(row["last_attempt_at"]) > now:
            raise Deferred("El reloj retrocedió; esperar a una ventana consistente.")
        if row and row["next_allowed_at"] and datetime.fromisoformat(row["next_allowed_at"]) > now:
            raise Deferred(f"Próxima oportunidad: {row['next_allowed_at']}")

    def reserve_attempt(
        self, run_id: str, now: datetime, *, first: bool, source: str = SOURCE
    ) -> None:
        """Commit ANTES de red. Un crash también consume un intento."""
        cutoff = (now - timedelta(hours=24)).isoformat()
        with self.connection:
            recent = self.connection.execute(
                "SELECT COUNT(*) FROM attempts WHERE source_id=? AND attempted_at>?",
                (source, (now - timedelta(seconds=60)).isoformat()),
            ).fetchone()[0]
            if recent >= 2:
                raise Deferred("Límite de dos intentos por minuto; no se envió otra request.")
            count = self.connection.execute(
                "SELECT COUNT(*) FROM attempts WHERE source_id=? AND attempted_at>?",
                (source, cutoff),
            ).fetchone()[0]
            if count >= 4:
                oldest = self.connection.execute(
                    "SELECT MIN(attempted_at) FROM attempts WHERE source_id=? AND attempted_at>?",
                    (source, cutoff),
                ).fetchone()[0]
                until = datetime.fromisoformat(oldest) + timedelta(hours=24)
                raise Deferred(
                    f"Cuota de cuatro intentos diarios agotada; próxima: {until.isoformat()}"
                )
            self.connection.execute(
                "INSERT INTO attempts(run_id,source_id,attempted_at) VALUES(?,?,?)",
                (run_id, source, now.isoformat()),
            )
            self.connection.execute(
                "UPDATE source_state SET last_attempt_at=? WHERE source_id=?",
                (now.isoformat(), source),
            )
            if first:
                self.connection.execute(
                    "UPDATE source_state SET next_allowed_at=? WHERE source_id=?",
                    ((now + timedelta(hours=12)).isoformat(), source),
                )

    def cooldown(self, until: datetime, *, source: str = SOURCE) -> None:
        with self.connection:
            self.connection.execute(
                "UPDATE source_state SET next_allowed_at=MAX(COALESCE(next_allowed_at,''),?) "
                "WHERE source_id=?",
                (until.isoformat(), source),
            )

    def disable(self, reason: str, *, source: str = SOURCE) -> None:
        with self.connection:
            self.connection.execute(
                "UPDATE source_state SET disabled_reason=? WHERE source_id=?", (reason, source)
            )

    def finish(
        self,
        run_id: str,
        now: datetime,
        status: str,
        message: str,
        metrics: dict[str, object],
        *,
        complete: bool = False,
    ) -> None:
        with self.connection:
            self._finish(run_id, now, status, message, metrics, complete=complete)

    def _finish(
        self,
        run_id: str,
        now: datetime,
        status: str,
        message: str,
        metrics: dict[str, object],
        *,
        complete: bool,
    ) -> None:
        self.connection.execute(
            "UPDATE runs SET finished_at=?,status=?,coverage=?,message=?,metrics=? WHERE run_id=?",
            (
                now.isoformat(),
                status,
                "complete" if complete else "incomplete",
                message,
                json.dumps(metrics, ensure_ascii=False),
                run_id,
            ),
        )

    def publish(
        self,
        run_id: str,
        batch: SourceBatch,
        now: datetime,
        metrics: dict[str, object],
        *,
        elapsed: Callable[[], float] | None = None,
    ) -> dict[str, int]:
        counts = {"new": 0, "updated": 0, "unchanged": 0}
        with self.connection:
            run = self.connection.execute(
                "SELECT source_id,scope FROM runs WHERE run_id=?", (run_id,)
            ).fetchone()
            if run is None:
                raise StorageError("Corrida desconocida.")
            baseline = self.connection.execute(
                "SELECT metrics FROM runs WHERE source_id=? AND scope=? "
                "AND status='succeeded' ORDER BY rowid DESC LIMIT 1",
                (run["source_id"], run["scope"]),
            ).fetchone()
            if baseline:
                previous_count = json.loads(baseline["metrics"]).get("valid", 0)
                if previous_count and len(batch.jobs) < previous_count * 0.2:
                    metrics["warnings"] = list(batch.warnings) + [
                        "Caída superior al 80% frente a la última colección completa."
                    ]
            for job in batch.jobs:
                if job.source_id != run["source_id"]:
                    raise StorageError("La oferta no pertenece a la fuente de la corrida.")
                key = f"{quote(job.source_id, safe='')}:{quote(job.source_job_id, safe='')}"
                previous = self.connection.execute(
                    "SELECT * FROM jobs WHERE job_key=?", (key,)
                ).fetchone()
                if previous and previous["normalizer_version"] != NORMALIZER_VERSION:
                    raise StorageError("El normalizador cambió; se requiere migración explícita.")
                digest = content_hash(job)
                kind = (
                    "new"
                    if previous is None
                    else ("unchanged" if previous["content_hash"] == digest else "updated")
                )
                stamp = now.isoformat()
                self.connection.execute(
                    """INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(job_key) DO UPDATE SET source_url=excluded.source_url,
                    payload=excluded.payload, content_hash=excluded.content_hash,
                    last_seen_at=excluded.last_seen_at, last_changed_at=excluded.last_changed_at""",
                    (
                        key,
                        job.source_id,
                        job.source_job_id,
                        job.source_url,
                        json.dumps(asdict(job), ensure_ascii=False),
                        digest,
                        NORMALIZER_VERSION,
                        previous["first_seen_at"] if previous else stamp,
                        stamp,
                        previous["last_changed_at"] if kind == "unchanged" else stamp,
                    ),
                )
                self.connection.execute("INSERT INTO run_items VALUES(?,?,?)", (run_id, key, kind))
                if kind != "unchanged":
                    before = None
                    if previous:
                        data = json.loads(previous["payload"])
                        for field in ("published_raw", "published_at", "source_updated_at"):
                            data.pop(field, None)
                        before = json.dumps(data, ensure_ascii=False, sort_keys=True)
                    self.connection.execute(
                        "INSERT INTO changes(run_id,job_key,kind,before_json,after_json) "
                        "VALUES(?,?,?,?,?)",
                        (run_id, key, kind, before, material_json(job)),
                    )
                counts[kind] += 1
            metrics.update(counts)
            if elapsed is not None:
                metrics["duration_seconds"] = round(elapsed(), 3)
            self._finish(
                run_id,
                now,
                "partial" if batch.rejections else "succeeded",
                "Publicación terminada.",
                metrics,
                complete=not batch.rejections,
            )
        return counts

    def status(self, *, source: str = SOURCE) -> dict[str, object]:
        run = self.connection.execute(
            "SELECT * FROM runs WHERE source_id=? ORDER BY rowid DESC LIMIT 1", (source,)
        ).fetchone()
        state = self.connection.execute(
            "SELECT * FROM source_state WHERE source_id=?", (source,)
        ).fetchone()
        published = self.connection.execute(
            "SELECT run_id,finished_at,status,coverage FROM runs WHERE source_id=? "
            "AND status IN ('succeeded','partial') ORDER BY rowid DESC LIMIT 1",
            (source,),
        ).fetchone()
        run_data = dict(run) if run else None
        if run_data:
            run_data["metrics"] = json.loads(run_data["metrics"])
        return {
            "database": str(self.path),
            "source": source,
            "jobs": self.connection.execute(
                "SELECT COUNT(*) FROM jobs WHERE source_id=?", (source,)
            ).fetchone()[0],
            "last_observed_at": self.connection.execute(
                "SELECT MAX(last_seen_at) FROM jobs WHERE source_id=?", (source,)
            ).fetchone()[0],
            "run": run_data,
            "last_published_run": dict(published) if published else None,
            "policy": dict(state) if state else None,
        }
