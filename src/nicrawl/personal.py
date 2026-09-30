"""Estados personales y ranking determinista, separados del contenido de origen."""

import json
import sqlite3
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from nicrawl.queries import Filters
from nicrawl.storage import Repository, StorageError, missing_job

STATES = ("unreviewed", "favorite", "dismissed")
FIELDS = ("title", "tags", "description")
WEIGHTS = {"title": 5, "tags": 3, "description": 1}


@dataclass(frozen=True)
class Preferences:
    want: tuple[str, ...] = ()
    avoid: tuple[str, ...] = ()
    mode: str | None = None
    fields: tuple[str, ...] = FIELDS

    def validate(self) -> None:
        if not self.want and not self.avoid and self.mode is None:
            raise ValueError("Indicá al menos --want, --avoid o --mode.")
        if len(self.want) + len(self.avoid) > 20:
            raise ValueError("Máximo 20 términos entre --want y --avoid.")
        for term in (*self.want, *self.avoid):
            if not term.strip() or term != term.strip() or len(term) > 80:
                raise ValueError("Cada término debe tener entre 1 y 80 caracteres.")
        if len({term.casefold() for term in self.want}) != len(self.want) or len(
            {term.casefold() for term in self.avoid}
        ) != len(self.avoid):
            raise ValueError("No repitas un mismo término en la misma regla.")
        if self.mode is not None and self.mode not in {"remote", "hybrid", "onsite"}:
            raise ValueError("Modo esperado: remote, hybrid u onsite.")
        if len(set(self.fields)) != len(self.fields) or any(
            field not in FIELDS for field in self.fields
        ):
            raise ValueError("Campos disponibles: title, tags, description.")
        if self.mode is None and not self.fields:
            raise ValueError("Activá al menos un campo de texto o indicá --mode.")


def score_job(job: dict[str, Any], preferences: Preferences) -> tuple[int, list[dict[str, Any]]]:
    """Suma razones verificables. Un desconocido nunca prueba elegibilidad."""
    reasons: list[dict[str, Any]] = []
    values = {
        "title": (job["title"],),
        "tags": tuple(job["tags"]),
        "description": (job["description_text"] or "",),
    }
    for preference, terms, direction in (
        ("want", preferences.want, 1),
        ("avoid", preferences.avoid, -1),
    ):
        for term in terms:
            for field in preferences.fields:
                if any(term.casefold() in value.casefold() for value in values[field]):
                    reasons.append(
                        {
                            "rule": preference,
                            "term": term,
                            "field": field,
                            "points": direction * WEIGHTS[field],
                        }
                    )
    if preferences.mode is not None and job["work_mode"] != "unknown":
        points = 2 if job["work_mode"] == preferences.mode else -2
        reasons.append(
            {
                "rule": "mode",
                "expected": preferences.mode,
                "observed": job["work_mode"],
                "points": points,
            }
        )
    return sum(reason["points"] for reason in reasons), reasons


def get_personal(connection: sqlite3.Connection, job_key: str) -> dict[str, str | None]:
    row = connection.execute(
        "SELECT state,note,updated_at FROM personal_state WHERE job_key=?", (job_key,)
    ).fetchone()
    return (
        {"state": row["state"], "note": row["note"], "updated_at": row["updated_at"]}
        if row
        else {"state": "unreviewed", "note": "", "updated_at": None}
    )


def mark(
    database: Path,
    job_key: str,
    *,
    state: str | None = None,
    note: str | None = None,
    clear_note: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    if state is not None and state not in STATES:
        raise ValueError("Estado esperado: unreviewed, favorite o dismissed.")
    if note is not None and clear_note:
        raise ValueError("--note y --clear-note son incompatibles.")
    if state is None and note is None and not clear_note:
        raise ValueError("Indicá --state, --note o --clear-note.")
    if note is not None and (len(note) > 2000 or "\x00" in note):
        raise ValueError("La nota no puede superar 2000 caracteres ni contener NUL.")
    instant = now or datetime.now(UTC)
    if instant.utcoffset() != timedelta(0):
        raise ValueError("El instante debe expresarse en UTC.")
    if not database.is_file():
        raise StorageError("No hay base local. Ejecutá collect primero.")
    with closing(Repository(database)) as repo:
        with repo.connection:
            repo.connection.execute("BEGIN IMMEDIATE")
            if (
                repo.connection.execute("SELECT 1 FROM jobs WHERE job_key=?", (job_key,)).fetchone()
                is None
            ):
                raise missing_job(repo.connection, job_key)
            previous = get_personal(repo.connection, job_key)
            new_state = state or previous["state"]
            new_note = "" if clear_note else (previous["note"] if note is None else note)
            if new_state == "unreviewed" and not new_note:
                repo.connection.execute("DELETE FROM personal_state WHERE job_key=?", (job_key,))
            else:
                repo.connection.execute(
                    "INSERT INTO personal_state(job_key,state,note,updated_at) VALUES(?,?,?,?) "
                    "ON CONFLICT(job_key) DO UPDATE SET "
                    "state=excluded.state,note=excluded.note,updated_at=excluded.updated_at",
                    (job_key, new_state, new_note, instant.isoformat()),
                )
            return {"job_key": job_key, "personal": get_personal(repo.connection, job_key)}


def rank(
    database: Path,
    preferences: Preferences,
    *,
    filters: Filters | None = None,
    limit: int = 20,
    include_dismissed: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    preferences.validate()
    if not 1 <= limit <= 200:
        raise ValueError("El límite debe estar entre 1 y 200.")
    observed = now or datetime.now(UTC)
    filters = filters or Filters()
    with closing(Repository(database, readonly=True)) as repo:
        repo.connection.execute("BEGIN")
        rows = repo.connection.execute("SELECT * FROM jobs")
        ranked: list[dict[str, Any]] = []
        for row in rows:
            job: dict[str, Any] = json.loads(row["payload"])
            if not filters.matches(job):
                continue
            personal = get_personal(repo.connection, row["job_key"])
            if personal["state"] == "dismissed" and not include_dismissed:
                continue
            for field in ("job_key", "first_seen_at", "last_seen_at", "last_changed_at"):
                job[field] = row[field]
            job["stale"] = observed - datetime.fromisoformat(row["last_seen_at"]) > timedelta(
                days=7
            )
            score, reasons = score_job(job, preferences)
            preview = {
                field: job[field]
                for field in (
                    "job_key",
                    "source_id",
                    "title",
                    "company",
                    "source_url",
                    "location_raw",
                    "work_mode",
                    "first_seen_at",
                    "last_seen_at",
                    "stale",
                )
            }
            ranked.append(
                {
                    "job": preview,
                    "score": score,
                    "reasons": reasons,
                    "personal": personal,
                }
            )
    ranked.sort(key=lambda item: item["job"]["job_key"])
    ranked.sort(key=lambda item: item["job"]["first_seen_at"], reverse=True)
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return {
        "rules_version": 1,
        "generated_at": observed.isoformat(),
        "preferences": asdict(preferences),
        "filters": asdict(filters),
        "include_dismissed": include_dismissed,
        "total": len(ranked),
        "limit": limit,
        "results": ranked[:limit],
        "note": "Puntaje heurístico; no determina elegibilidad ni vigencia de la oferta.",
    }
