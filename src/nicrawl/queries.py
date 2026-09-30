"""Consultas locales en una instantánea SQLite; ninguna adquisición de red."""

import json
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from nicrawl.storage import Repository, StorageError, missing_job


@dataclass(frozen=True)
class Filters:
    query: str = ""
    company: str = ""
    source: str = ""
    location_text: str = ""

    def matches(self, job: dict[str, Any]) -> bool:
        def contains(needle: str, value: str | None) -> bool:
            return needle.casefold() in (value or "").casefold()

        return (
            (not self.source or job["source_id"] == self.source)
            and contains(self.company, job["company"])
            and contains(self.location_text, job["location_raw"])
            and any(
                contains(self.query, job[field])
                for field in ("title", "company", "description_text")
            )
        )


def _job(row: Any, now: datetime) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(row["payload"])
    for field in ("job_key", "first_seen_at", "last_seen_at", "last_changed_at"):
        result[field] = row[field]
    result["stale"] = now - datetime.fromisoformat(row["last_seen_at"]) > timedelta(days=7)
    return result


def search(
    database: Path,
    filters: Filters | None = None,
    *,
    limit: int | None = 20,
    now: datetime | None = None,
) -> dict[str, Any]:
    observed = now or datetime.now(UTC)
    filters = filters or Filters()
    with closing(Repository(database, readonly=True)) as repo:
        repo.connection.execute("BEGIN")
        state = (
            repo.status(source=filters.source)
            if filters.source
            else {
                source: repo.status(source=source) for source in ("remotive", "greenhouse:gitlab")
            }
        )
        rows = repo.connection.execute(
            "SELECT * FROM jobs ORDER BY first_seen_at DESC, job_key ASC"
        )
        jobs = [job for row in rows if filters.matches(job := _job(row, observed))]
    return {
        "schema_version": 1,
        "filters": asdict(filters),
        "generated_at": observed.isoformat(),
        "source_status": state,
        "total": len(jobs),
        "limit": limit,
        "jobs": jobs if limit is None else jobs[:limit],
    }


def show(database: Path, job_key: str) -> dict[str, Any]:
    from nicrawl.personal import get_personal

    with closing(Repository(database, readonly=True)) as repo:
        repo.connection.execute("BEGIN")
        row = repo.connection.execute("SELECT * FROM jobs WHERE job_key=?", (job_key,)).fetchone()
        if row is None:
            raise missing_job(repo.connection, job_key)
        return {
            "source_status": repo.status(source=row["source_id"]),
            "job": _job(row, datetime.now(UTC)),
            "personal": get_personal(repo.connection, job_key),
        }


def changes(
    database: Path, *, run: str = "latest", source: str = "remotive", limit: int = 20
) -> dict[str, Any]:
    with closing(Repository(database, readonly=True)) as repo:
        repo.connection.execute("BEGIN")
        clause = "" if run == "latest" else " AND run_id=?"
        params = (source,) if run == "latest" else (source, run)
        row = repo.connection.execute(
            "SELECT * FROM runs WHERE source_id=? AND status IN ('succeeded','partial')"
            + clause
            + " ORDER BY rowid DESC LIMIT 1",
            params,
        ).fetchone()
        if row is None:
            raise StorageError("No hay una corrida publicada para esa selección.")
        published = dict(row)
        published["metrics"] = json.loads(published["metrics"])
        total = repo.connection.execute(
            "SELECT COUNT(*) FROM changes WHERE run_id=?", (row["run_id"],)
        ).fetchone()[0]
        items = []
        for change in repo.connection.execute(
            "SELECT * FROM changes WHERE run_id=? ORDER BY job_key ASC LIMIT ?",
            (row["run_id"], limit),
        ):
            before = json.loads(change["before_json"]) if change["before_json"] else None
            after = json.loads(change["after_json"])
            fields = sorted(key for key in after if before is None or before.get(key) != after[key])
            items.append(
                {
                    "job_key": change["job_key"],
                    "kind": change["kind"],
                    "fields": fields,
                    "before": before,
                    "after": after,
                }
            )
        return {
            "source_status": repo.status(),
            "published_run": published,
            "total": total,
            "limit": limit,
            "changes": items,
        }
