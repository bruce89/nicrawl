"""Seguimiento personal transaccional, separado de la colección y sin red."""

import hashlib
import json
import os
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
MATERIALS_SCHEMA = (
    """CREATE TABLE profile_versions(
        version INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT NOT NULL,
        cv_text TEXT NOT NULL, cv_sha256 TEXT NOT NULL, created_at TEXT NOT NULL)""",
    """CREATE TABLE profile_claims(
        profile_version INTEGER NOT NULL REFERENCES profile_versions(version),
        claim_id TEXT NOT NULL, statement TEXT NOT NULL, evidence TEXT NOT NULL,
        evidence_sha256 TEXT NOT NULL, PRIMARY KEY(profile_version,claim_id))""",
    """CREATE TABLE drafts(
        id TEXT PRIMARY KEY, application_id TEXT NOT NULL REFERENCES applications(id),
        current_version INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""",
    """CREATE TABLE draft_versions(
        draft_id TEXT NOT NULL REFERENCES drafts(id), version INTEGER NOT NULL,
        profile_version INTEGER NOT NULL REFERENCES profile_versions(version),
        opening TEXT NOT NULL, claim_ids_json TEXT NOT NULL, questions_json TEXT NOT NULL,
        content_sha256 TEXT NOT NULL, created_at TEXT NOT NULL,
        PRIMARY KEY(draft_id,version))""",
)
CV_MAX_CHARS = 300_000
CLAIM_MAX = 50
OPENING_MAX = 2_000
QUESTIONS_MAX = 20
QUESTION_MAX = 500


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


class ClaimInput(Contract):
    statement: Annotated[str, Field(min_length=1, max_length=500)]
    evidence: Annotated[str, Field(min_length=1, max_length=2000)]


class ProfileInput(Contract):
    label: Annotated[str, Field(min_length=1, max_length=80)]
    cv_text: Annotated[str, Field(min_length=1, max_length=CV_MAX_CHARS)]
    claims: Annotated[list[ClaimInput], Field(min_length=1, max_length=CLAIM_MAX)]

    @model_validator(mode="after")
    def evidence_is_verbatim_and_unique(self) -> Self:
        if not self.label.strip():
            raise ValueError("El nombre de versión está vacío.")
        if not self.cv_text.strip():
            raise ValueError("El CV está vacío.")
        for claim in self.claims:
            if claim.statement != claim.statement.strip() or not claim.statement:
                raise ValueError(
                    "Cada afirmación debe tener texto y no incluir espacios exteriores."
                )
            if claim.evidence != claim.evidence.strip() or claim.evidence not in self.cv_text:
                raise ValueError("Cada evidencia debe ser una cita literal del CV aportado.")
        normalized = [claim.statement.casefold() for claim in self.claims]
        if len(set(normalized)) != len(normalized):
            raise ValueError("No repitas afirmaciones en una versión del perfil.")
        return self


class DraftInput(Contract):
    profile_version: Annotated[int, Field(ge=1)]
    claim_ids: Annotated[
        list[Annotated[str, Field(pattern=r"^E\d{2}$")]], Field(max_length=CLAIM_MAX)
    ] = Field(default_factory=list)
    opening: Annotated[str, Field(max_length=OPENING_MAX)] = ""
    questions: Annotated[
        list[Annotated[str, Field(min_length=1, max_length=QUESTION_MAX)]],
        Field(max_length=QUESTIONS_MAX),
    ] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_claims_and_questions(self) -> Self:
        if len(set(self.claim_ids)) != len(self.claim_ids):
            raise ValueError("No repitas una afirmación en el borrador.")
        if any(item != item.strip() for item in self.questions):
            raise ValueError("Las preguntas no deben tener espacios al inicio o al final.")
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
            for statement in MATERIALS_SCHEMA:
                connection.execute(statement)
            connection.execute(f"PRAGMA application_id={APP_ID}")
            connection.execute("PRAGMA user_version=2")
        elif app_id == APP_ID and version == 1:
            if write:
                for statement in MATERIALS_SCHEMA:
                    connection.execute(statement)
                connection.execute("PRAGMA user_version=2")
        elif app_id != APP_ID or version != 2:
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


def _profile(connection: sqlite3.Connection, version: int | None = None) -> dict[str, Any]:
    row = connection.execute(
        "SELECT * FROM profile_versions WHERE version=?"
        if version is not None
        else "SELECT * FROM profile_versions ORDER BY version DESC LIMIT 1",
        (version,) if version is not None else (),
    ).fetchone()
    if row is None:
        raise NotFound("Versión de perfil no encontrada.")
    result = dict(row)
    result["claims"] = [
        dict(claim)
        for claim in connection.execute(
            "SELECT claim_id,statement,evidence,evidence_sha256 FROM profile_claims "
            "WHERE profile_version=? ORDER BY claim_id",
            (row["version"],),
        )
    ]
    return result


def save_profile(database: Path, request: ProfileInput) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    digest = hashlib.sha256(request.cv_text.encode("utf-8")).hexdigest()
    with _connect(database, write=True) as connection:
        cursor = connection.execute(
            "INSERT INTO profile_versions(label,cv_text,cv_sha256,created_at) VALUES(?,?,?,?)",
            (request.label.strip(), request.cv_text, digest, now),
        )
        version = cursor.lastrowid
        connection.executemany(
            "INSERT INTO profile_claims VALUES(?,?,?,?,?)",
            [
                (
                    version,
                    f"E{i:02}",
                    claim.statement,
                    claim.evidence,
                    hashlib.sha256(claim.evidence.encode("utf-8")).hexdigest(),
                )
                for i, claim in enumerate(request.claims, 1)
            ],
        )
        profile = _profile(connection, version)
        profile.pop("cv_text", None)
        return profile


def list_profiles(database: Path) -> dict[str, Any]:
    if not tracker_path(database).exists():
        return {"profiles": []}
    with _connect(database) as connection:
        if connection.execute("PRAGMA user_version").fetchone()[0] < 2:
            return {"profiles": []}
        rows = connection.execute(
            "SELECT version,label,cv_sha256,created_at FROM profile_versions ORDER BY version DESC"
        )
        return {"profiles": [dict(row) for row in rows]}


def get_profile(database: Path, version: int | None = None) -> dict[str, Any]:
    if not tracker_path(database).exists():
        raise NotFound("Versión de perfil no encontrada.")
    with _connect(database) as connection:
        return _profile(connection, version)


def _draft_preview(
    application: dict[str, Any],
    profile: dict[str, Any],
    opening: str,
    claims: list[dict[str, Any]],
    questions: list[str],
) -> str:
    lines = [
        f"# Borrador — {application['title']} — {application['company']}",
        f"Referencia: {application['url']}",
        "",
        "BORRADOR: requiere revisión humana.",
        f"Perfil local versión {profile['version']} ({profile['label']}).",
    ]
    if opening:
        lines += [
            "",
            "### Apertura escrita por el usuario",
            opening,
            "Verificar contenido y adecuación antes de usar.",
        ]
    lines += ["", "### Afirmaciones seleccionadas"]
    if claims:
        lines.extend(f"- {claim['statement']} [{claim['claim_id']}]" for claim in claims)
    else:
        lines.append("- No se seleccionaron afirmaciones del perfil.")
    lines += ["", "### Evidencia literal en el CV"]
    if claims:
        lines.extend(f"- {claim['claim_id']}: “{claim['evidence']}”" for claim in claims)
    else:
        lines.append("- Sin citas seleccionadas.")
    lines.append(
        "La cita exacta aparece en el CV aportado; esto no verifica que sea actual ni verdadera."
    )
    lines += ["", "### Preguntas pendientes"]
    lines.extend(f"- {question}" for question in questions)
    if not questions:
        lines.append("- Sin preguntas registradas; revisar el aviso y el perfil antes de usar.")
    return "\n".join(lines) + "\n"


def create_draft(database: Path, application_id: str, request: DraftInput) -> dict[str, Any]:
    now, identifier = datetime.now(UTC).isoformat(), str(uuid4())
    with _connect(database, write=True) as connection:
        application = _detail(connection, application_id)["application"]
        profile = _profile(connection, request.profile_version)
        claims_by_id = {item["claim_id"]: item for item in profile["claims"]}
        if not set(request.claim_ids) <= set(claims_by_id):
            raise ValueError("La selección incluye afirmaciones fuera de la versión del perfil.")
        claims = [claims_by_id[key] for key in request.claim_ids]
        preview = _draft_preview(application, profile, request.opening, claims, request.questions)
        digest = hashlib.sha256(preview.encode("utf-8")).hexdigest()
        connection.execute(
            "INSERT INTO drafts VALUES(?,?,1,?,?)", (identifier, application_id, now, now)
        )
        connection.execute(
            "INSERT INTO draft_versions VALUES(?,?,?,?,?,?,?,?)",
            (
                identifier,
                1,
                request.profile_version,
                request.opening,
                json.dumps(request.claim_ids),
                json.dumps(request.questions),
                digest,
                now,
            ),
        )
    return show_draft(database, identifier)


def show_draft(database: Path, draft_id: str, version: int | None = None) -> dict[str, Any]:
    if not tracker_path(database).exists():
        raise NotFound("Borrador no encontrado.")
    with _connect(database) as connection:
        head = connection.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone()
        if head is None:
            raise NotFound("Borrador no encontrado.")
        chosen = version or head["current_version"]
        row = connection.execute(
            "SELECT * FROM draft_versions WHERE draft_id=? AND version=?", (draft_id, chosen)
        ).fetchone()
        if row is None:
            raise NotFound("Versión de borrador no encontrada.")
        app = _detail(connection, head["application_id"])["application"]
        profile = _profile(connection, row["profile_version"])
        ids, questions = json.loads(row["claim_ids_json"]), json.loads(row["questions_json"])
        claims = [claim for claim in profile["claims"] if claim["claim_id"] in ids]
        return {
            "id": draft_id,
            "application_id": head["application_id"],
            "version": chosen,
            "current_version": head["current_version"],
            "profile_version": profile["version"],
            "claim_ids": ids,
            "opening": row["opening"],
            "questions": questions,
            "content_sha256": row["content_sha256"],
            "preview": _draft_preview(app, profile, row["opening"], claims, questions),
        }


def revise_draft(
    database: Path, draft_id: str, expected_version: int, request: DraftInput
) -> dict[str, Any]:
    with _connect(database, write=True) as connection:
        head = connection.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone()
        if head is None:
            raise NotFound("Borrador no encontrado.")
        if head["current_version"] != expected_version:
            raise Conflict("Versión desactualizada: recargá el borrador antes de editar.")
        profile = _profile(connection, request.profile_version)
        claims_by_id = {item["claim_id"]: item for item in profile["claims"]}
        if not set(request.claim_ids) <= set(claims_by_id):
            raise ValueError("La selección incluye afirmaciones fuera de la versión del perfil.")
        app = _detail(connection, head["application_id"])["application"]
        claims = [claims_by_id[key] for key in request.claim_ids]
        preview = _draft_preview(app, profile, request.opening, claims, request.questions)
        now, version = datetime.now(UTC).isoformat(), expected_version + 1
        connection.execute(
            "INSERT INTO draft_versions VALUES(?,?,?,?,?,?,?,?)",
            (
                draft_id,
                version,
                request.profile_version,
                request.opening,
                json.dumps(request.claim_ids),
                json.dumps(request.questions),
                hashlib.sha256(preview.encode("utf-8")).hexdigest(),
                now,
            ),
        )
        connection.execute(
            "UPDATE drafts SET current_version=?,updated_at=? WHERE id=?", (version, now, draft_id)
        )
    return show_draft(database, draft_id)


def list_drafts(database: Path, application_id: str) -> dict[str, Any]:
    if not tracker_path(database).exists():
        raise NotFound("Candidatura no encontrada.")
    with _connect(database) as connection:
        _detail(connection, application_id)
        if connection.execute("PRAGMA user_version").fetchone()[0] < 2:
            return {"drafts": []}
        rows = connection.execute(
            "SELECT * FROM drafts WHERE application_id=? ORDER BY updated_at DESC",
            (application_id,),
        )
        return {"drafts": [dict(row) for row in rows]}


def export_draft(
    database: Path, draft_id: str, destination: Path, version: int | None = None
) -> Path:
    draft = show_draft(database, draft_id, version)
    target = Path(destination).absolute()
    protected = {Path(database).resolve(), tracker_path(database).resolve()}
    if target.resolve(strict=False) in protected:
        raise ValueError("El destino coincide con una base de datos local.")
    descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(draft["preview"])
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return target
