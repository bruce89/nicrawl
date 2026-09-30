"""Vista local del próximo intento permitido; no reserva cuota ni agenda procesos."""

from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

from nicrawl.storage import Repository

SOURCES = ("remotive", "greenhouse:gitlab")


def plan(database: Path, *, now: datetime | None = None) -> dict[str, object]:
    instant = now or datetime.now(UTC)
    if instant.utcoffset() != timedelta(0):
        raise ValueError("El instante del plan debe expresarse en UTC.")
    result: dict[str, object] = {}
    with closing(Repository(database, readonly=True)) as repository:
        repository.connection.execute("BEGIN")
        for source in SOURCES:
            policy = repository.connection.execute(
                "SELECT * FROM source_state WHERE source_id=?", (source,)
            ).fetchone()
            if policy is None:
                result[source] = {
                    "state": "uninitialized",
                    "ready_at": instant.isoformat(),
                    "reason": "Sin intentos locales; una recolección creará su estado.",
                }
                continue
            if policy["disabled_reason"]:
                result[source] = {
                    "state": "disabled",
                    "ready_at": None,
                    "reason": policy["disabled_reason"],
                }
                continue
            candidate = instant
            reasons: list[str] = []
            for field in ("last_attempt_at", "next_allowed_at"):
                raw = policy[field]
                if raw:
                    stamp = datetime.fromisoformat(raw)
                    if stamp > candidate:
                        candidate = stamp
                        reasons.append(field)
            for window, maximum in ((timedelta(seconds=60), 2), (timedelta(hours=24), 4)):
                row = repository.connection.execute(
                    "SELECT COUNT(*),MIN(attempted_at) FROM attempts "
                    "WHERE source_id=? AND attempted_at>?",
                    (source, (instant - window).isoformat()),
                ).fetchone()
                if row[0] >= maximum:
                    cutoff = datetime.fromisoformat(row[1]) + window
                    if cutoff > candidate:
                        candidate = cutoff
                        reasons.append(f"ventana_{int(window.total_seconds())}s")
            result[source] = {
                "state": "ready" if candidate <= instant else "deferred",
                "ready_at": candidate.isoformat(),
                "reason": ", ".join(reasons) if reasons else "Cuota local disponible.",
            }
    return {
        "database": str(database.resolve()),
        "checked_at": instant.isoformat(),
        "sources": result,
        "note": "Estimación local; collect revalida bajo bloqueo antes de enviar.",
    }
