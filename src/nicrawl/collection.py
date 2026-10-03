"""Caso de uso: coordinar recursos sin mezclar SQL, parsing y presentación."""

import sqlite3
import ssl
from contextlib import closing
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx

from nicrawl.acquisition import Clock, FetchError, FetchStats, SystemClock, fetch
from nicrawl.locking import collection_lock
from nicrawl.sources import greenhouse, remotive
from nicrawl.sources.remotive import SourceFormatError
from nicrawl.storage import Deferred, Repository, StorageError


@dataclass(frozen=True)
class RunResult:
    run_id: str
    status: str
    message: str
    metrics: dict[str, object]


def collect(
    database: Path,
    *,
    clock: Clock | None = None,
    transport: httpx.BaseTransport | None = None,
    max_bytes: int = 10 * 1024 * 1024,
    source_id: str = remotive.SOURCE,
) -> RunResult:
    if source_id == remotive.SOURCE:
        endpoint, scope, adapter, parser, host = (
            remotive.ENDPOINT,
            remotive.SCOPE,
            remotive.ADAPTER_VERSION,
            remotive.parse_response,
            "remotive.com",
        )
    elif source_id == greenhouse.SOURCE:
        endpoint, scope, adapter, parser, host = (
            greenhouse.ENDPOINT,
            greenhouse.SCOPE,
            greenhouse.ADAPTER_VERSION,
            greenhouse.parse_response,
            "boards-api.greenhouse.io",
        )
    else:
        raise ValueError("Fuente no habilitada.")
    clock = clock or SystemClock()
    database = database.resolve()
    with collection_lock(database), closing(Repository(database)) as repository:
        run_id = repository.start_run(
            clock.now(), source=source_id, scope=scope, adapter_version=adapter
        )
        started = clock.monotonic()
        stats = FetchStats()
        metrics: dict[str, object] = {}
        try:
            repository.gate(clock.now(), source=source_id)
            with httpx.Client(
                transport=transport,
                verify=ssl.create_default_context(),
                headers={
                    "User-Agent": "nicrawl/0.10.0 (personal learning collector)",
                    "Accept": "application/json",
                },
                follow_redirects=False,
            ) as client:
                body = fetch(
                    client,
                    repository,
                    run_id,
                    clock,
                    stats,
                    deadline=started + 120,
                    max_bytes=max_bytes,
                    endpoint=endpoint,
                    source=source_id,
                    allowed_host=host,
                )
            batch = parser(body)
            metrics = {
                **asdict(stats),
                "candidates": batch.candidates,
                "valid": len(batch.jobs),
                "rejected": len(batch.rejections),
                "duplicates": batch.duplicates,
                "rejections": [asdict(item) for item in batch.rejections],
                "warnings": list(batch.warnings),
                "duration_seconds": round(clock.monotonic() - started, 3),
            }
            if not batch.jobs and batch.rejections:
                raise SourceFormatError("Todos los candidatos son inválidos; colección conservada.")
            if clock.monotonic() >= started + 120:
                raise FetchError("Deadline agotado antes de publicar; colección conservada.")
            repository.publish(
                run_id, batch, clock.now(), metrics, elapsed=lambda: clock.monotonic() - started
            )
            status = "partial" if batch.rejections else "succeeded"
            return RunResult(run_id, status, "Publicación terminada.", metrics)
        except KeyboardInterrupt:
            repository.finish(
                run_id,
                clock.now(),
                "interrupted",
                "Interrupción del usuario.",
                {**asdict(stats), "duration_seconds": clock.monotonic() - started},
            )
            raise
        except (
            Deferred,
            FetchError,
            SourceFormatError,
            StorageError,
            sqlite3.Error,
            OSError,
        ) as error:
            status = "deferred" if isinstance(error, Deferred) else "failed"
            metrics.update(asdict(stats))
            metrics.update(
                new=0,
                updated=0,
                unchanged=0,
                duration_seconds=round(clock.monotonic() - started, 3),
            )
            repository.finish(run_id, clock.now(), status, str(error), metrics)
            return RunResult(run_id, status, str(error), metrics)
