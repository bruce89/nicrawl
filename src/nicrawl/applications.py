"""Seguimiento personal transaccional, separado de la colección y sin red."""

import re
import sqlite3
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal, Self
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from nicrawl import queries

State = Literal["draft", "submitted", "interview", "closed"]
STATES = ("draft", "submitted", "interview", "closed")
APP_ID = 0x4E434150
SCHEMA = (
    """CREATE TABLE applications(
        id TEXT PRIMARY KEY, job_key TEXT, title TEXT NOT NULL, company TEXT NOT NULL,
        url TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN
        ('draft','submitted','interview','closed')), revision INTEGER NOT NULL,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""",
    """CREATE TABLE identities(identity TEXT PRIMARY KEY,
        application_id TEXT NOT NULL REFERENCES applications(id))""",
    """CREATE TABLE events(application_id TEXT NOT NULL REFERENCES applications(id),
        revision INTEGER NOT NULL, at TEXT NOT NULL, kind TEXT NOT NULL,
        from_state TEXT, to_state TEXT NOT NULL, reason TEXT NOT NULL,
        PRIMARY KEY(application_id,revision))""",
)


class ApplicationError(ValueError):
    pass


class NotFound(ApplicationError):
    pass


class Conflict(ApplicationError):
    pass


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Create(Contract):
    job_key: Annotated[str, Field(min_length=1, max_length=512)] | None = None
    url: Annotated[str, Field(min_length=1, max_length=2048)] | None = None
    title: Annotated[str, Field(min_length=1, max_length=400)] | None = None
    company: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    reason: Annotated[str, Field(max_length=2000)] = ""

    @model_validator(mode="after")
    def one_origin(self) -> Self:
        if self.job_key:
            if any(value is not None for value in (self.url, self.title, self.company)):
                raise ValueError("Usá job_key o referencia manual, no ambos.")
        elif not all(value and value.strip() for value in (self.url, self.title, self.company)):
            raise ValueError("Una referencia manual requiere url, title y company.")
        return self


class Update(Contract):
    state: State
    expected_revision: Annotated[int, Field(ge=1)]
    reason: Annotated[str, Field(min_length=1, max_length=2000)]

    @model_validator(mode="after")
    def meaningful_reason(self) -> Self:
        if not self.reason.strip():
            raise ValueError("Indicá un motivo para registrar o corregir el estado.")
        return self


def tracker_path(database: Path) -> Path:
    return Path(str(database.resolve()) + ".applications.sqlite3")


def canonical_url(value: str) -> str:
    if value != value.strip() or any(unicodedata.category(c).startswith("C") for c in value):
        raise ValueError("URL con espacios exteriores o caracteres de control.")
    parts = urlsplit(value)
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or "\\" in value
        or any(c.isspace() for c in value)
    ):
        raise ValueError("Usá una URL HTTP(S) absoluta, sin credenciales ni espacios.")
    host = parts.hostname.lower()
    port = parts.port  # Valida puertos malformados antes de cualquier escritura.
    if host in {"linkedin.com", "www.linkedin.com", "m.linkedin.com"} and port in (None, 443):
        match = re.fullmatch(r"/jobs/view/(?:[^/]+-)?([0-9]+)/?", parts.path)
        if match and parts.scheme == "https":
            return f"https://www.linkedin.com/jobs/view/{match[1]}"
    authority = f"[{host}]" if ":" in host else host
    if port is not None and (parts.scheme, port) not in {("https", 443), ("http", 80)}:
        authority += f":{port}"
    # Conservar parámetros funcionales y su orden; retirar solo utm_* y fragmento.
    query = urlencode(
        [
            (k, v)
            for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if not k.lower().startswith("utm_")
        ]
    )
    return urlunsplit((parts.scheme, authority, parts.path or "/", query, ""))


@contextmanager
def _connect(database: Path, *, write: bool = False) -> Iterator[sqlite3.Connection]:
    path = tracker_path(database)
    if path.is_symlink() or (path.exists() and database.exists() and path.samefile(database)):
        raise ApplicationError("Ruta de seguimiento inválida.")
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path.as_uri() + ("?mode=rwc" if write else "?mode=ro"), uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    try:
        connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
        app_id = connection.execute("PRAGMA application_id").fetchone()[0]
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        if not tables and app_id == 0 and version == 0 and write:
            for statement in SCHEMA:
                connection.execute(statement)
            connection.execute(f"PRAGMA application_id={APP_ID}")
            connection.execute("PRAGMA user_version=1")
        elif app_id != APP_ID or version != 1:
            raise ApplicationError("Base de candidaturas ajena o de versión incompatible.")
        yield connection
        if write:
            connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def _detail(connection: sqlite3.Connection, application_id: str) -> dict[str, Any]:
    row = connection.execute("SELECT * FROM applications WHERE id=?", (application_id,)).fetchone()
    if row is None:
        raise NotFound("Candidatura no encontrada.")
    return {
        "application": dict(row),
        "history": [
            dict(item)
            for item in connection.execute(
                "SELECT * FROM events WHERE application_id=? ORDER BY revision", (application_id,)
            )
        ],
    }


def show(database: Path, application_id: str) -> dict[str, Any]:
    if not tracker_path(database).exists():
        raise NotFound("Candidatura no encontrada.")
    with _connect(database) as connection:
        return _detail(connection, application_id)


def list_applications(database: Path, *, state: str = "", limit: int = 50) -> dict[str, Any]:
    if state and state not in STATES:
        raise ValueError("Estado desconocido.")
    if not 1 <= limit <= 200:
        raise ValueError("limit debe estar entre 1 y 200.")
    if not tracker_path(database).exists():
        return {"total": 0, "limit": limit, "applications": []}
    with _connect(database) as connection:
        where = " WHERE state=?" if state else ""
        args = (state,) if state else ()
        total = connection.execute("SELECT count(*) FROM applications" + where, args).fetchone()[0]
        rows = connection.execute(
            "SELECT * FROM applications" + where + " ORDER BY updated_at DESC,id LIMIT ?",
            (*args, limit),
        )
        return {"total": total, "limit": limit, "applications": [dict(row) for row in rows]}


def create(database: Path, request: Create) -> dict[str, Any]:
    if request.job_key:
        job = queries.show(database, request.job_key)["job"]
        title, company, url = job["title"], job["company"], job["source_url"]
    else:
        title, company, url = request.title, request.company, request.url
    assert isinstance(url, str) and isinstance(title, str) and isinstance(company, str)
    url_key = canonical_url(url)
    identities = ["url:" + url_key]
    if request.job_key:
        identities.append("job:" + request.job_key)
    with _connect(database, write=True) as connection:
        matches = {
            row[0]
            for identity in identities
            for row in connection.execute(
                "SELECT application_id FROM identities WHERE identity=?", (identity,)
            )
        }
        if matches:
            if len(matches) != 1:
                raise Conflict("La clave y la URL corresponden a candidaturas diferentes.")
            # No fusionar ni vincular silenciosamente referencias o notas.
            return {"created": False, **_detail(connection, matches.pop())}
        now = datetime.now(UTC).isoformat()
        identifier = str(uuid4())
        connection.execute(
            "INSERT INTO applications VALUES(?,?,?,?,?,'draft',1,?,?)",
            (identifier, request.job_key, title.strip(), company.strip(), url, now, now),
        )
        connection.executemany(
            "INSERT INTO identities VALUES(?,?)",
            [(identity, identifier) for identity in identities],
        )
        connection.execute(
            "INSERT INTO events VALUES(?,1,?,'created',NULL,'draft',?)",
            (identifier, now, request.reason),
        )
        return {"created": True, **_detail(connection, identifier)}


def update(database: Path, application_id: str, request: Update) -> dict[str, Any]:
    if not tracker_path(database).exists():
        raise NotFound("Candidatura no encontrada.")
    with _connect(database, write=True) as connection:
        previous = _detail(connection, application_id)["application"]
        if previous["revision"] != request.expected_revision:
            raise Conflict("Revisión desactualizada: recargá la candidatura antes de guardar.")
        now = datetime.now(UTC).isoformat()
        revision = previous["revision"] + 1
        connection.execute(
            "UPDATE applications SET state=?,revision=?,updated_at=? WHERE id=?",
            (request.state, revision, now, application_id),
        )
        connection.execute(
            "INSERT INTO events VALUES(?,?,?,'updated',?,?,?)",
            (
                application_id,
                revision,
                now,
                previous["state"],
                request.state,
                request.reason.strip(),
            ),
        )
        return _detail(connection, application_id)
