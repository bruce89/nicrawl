"""Muestras fijas y etiquetas humanas: medir utilidad sin inferirla de favoritos."""

import hashlib
import json
import sqlite3
from collections import Counter
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated, Any, Literal

from pydantic import Field

from nicrawl import queries
from nicrawl.personal import rank
from nicrawl.saved_searches import SavedSearch, StrictModel, get_saved, read_json
from nicrawl.storage import Repository


class SampleJob(StrictModel):
    job_key: str
    source_id: str
    source_url: str
    title: str
    company: str
    location_raw: str | None
    work_mode: str
    last_seen_at: str
    stale: bool
    description_text: str | None
    tags: list[str]


class RankedKey(StrictModel):
    job_key: str
    score: int
    reasons: list[dict[str, Any]]


class Sample(StrictModel):
    profile: SavedSearch
    generated_at: str
    k: Annotated[int, Field(ge=1, le=20)]
    rules_version: Literal[1]
    include_dismissed: Literal[True] = True
    candidate_total: Annotated[int, Field(ge=0)]
    source_counts: dict[str, dict[str, int]]
    list_order: Annotated[list[str], Field(max_length=20)]
    rank_order: Annotated[list[RankedKey], Field(max_length=20)]
    jobs: Annotated[list[SampleJob], Field(max_length=40)]


class Snapshot(StrictModel):
    schema_version: Literal[1] = 1
    snapshot_id: str
    sample: Sample
    # export_file añade fecha de publicación; no participa de la identidad.
    exported_at: str | None = None


class Label(StrictModel):
    job_key: str
    verdict: Literal["useful", "not_useful", "unknown", "pending"] = "pending"
    reason: Annotated[str, Field(max_length=500)] = ""


class Labels(StrictModel):
    schema_version: Literal[1] = 1
    snapshot_id: str
    labels: Annotated[list[Label], Field(max_length=40)]
    exported_at: str | None = None


def _identity(sample: Sample) -> str:
    payload = json.dumps(
        sample.model_dump(), sort_keys=True, ensure_ascii=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def capture(database: Path, name: str, *, k: int = 10) -> Snapshot:
    if not 1 <= k <= 20:
        raise ValueError("k debe estar entre 1 y 20.")
    profile = get_saved(database, name)
    profile.preferences().validate()
    now = datetime.now(UTC)
    # SQLite backup ofrece una instantánea consistente aun si otro proceso publica.
    # La copia temporal puede contener notas; se elimina y nunca se exportan.
    with TemporaryDirectory(prefix="nicrawl-evaluation-") as directory:
        frozen = Path(directory) / "snapshot.sqlite3"
        with closing(Repository(database, readonly=True)) as source:
            with closing(sqlite3.connect(frozen)) as target:
                source.connection.backup(target)
        collection = queries.search(frozen, limit=None, now=now)
        selection = queries.search(frozen, profile.filters(), limit=None, now=now)
        ranked = rank(
            frozen,
            profile.preferences(),
            filters=profile.filters(),
            limit=k,
            include_dismissed=True,
            now=now,
        )
    baseline = [job["job_key"] for job in selection["jobs"][:k]]
    ranked_keys = [
        RankedKey(job_key=item["job"]["job_key"], score=item["score"], reasons=item["reasons"])
        for item in ranked["results"]
    ]
    keys = set(baseline) | {item.job_key for item in ranked_keys}
    jobs = [
        SampleJob.model_validate({field: job[field] for field in SampleJob.model_fields})
        for job in selection["jobs"]
        if job["job_key"] in keys
    ]
    totals = Counter(job["source_id"] for job in collection["jobs"])
    candidates = Counter(job["source_id"] for job in selection["jobs"])
    counts = {
        source: {
            "collection": totals[source],
            "candidates": candidates[source],
            "missing_location": sum(
                not job["location_raw"] for job in selection["jobs"] if job["source_id"] == source
            ),
            "stale": sum(job["stale"] for job in selection["jobs"] if job["source_id"] == source),
        }
        for source in sorted({"remotive", "greenhouse:gitlab"} | totals.keys())
    }
    sample = Sample(
        profile=profile,
        generated_at=now.isoformat(),
        k=k,
        rules_version=ranked["rules_version"],
        candidate_total=selection["total"],
        source_counts=counts,
        list_order=baseline,
        rank_order=ranked_keys,
        jobs=jobs,
    )
    snapshot = Snapshot(snapshot_id=_identity(sample), sample=sample)
    if len(snapshot.model_dump_json().encode("utf-8")) > 8 * 1024 * 1024:
        raise ValueError("Muestra mayor a 8 MiB; reducir k.")
    return snapshot


def load_snapshot(path: Path) -> Snapshot:
    snapshot = Snapshot.model_validate(read_json(path, max_bytes=16 * 1024 * 1024))
    if snapshot.snapshot_id != _identity(snapshot.sample):
        raise ValueError("La muestra cambió; conservar el original y generar otra evaluación.")
    keys = [job.job_key for job in snapshot.sample.jobs]
    baseline = snapshot.sample.list_order
    ranked = [item.job_key for item in snapshot.sample.rank_order]
    if (
        len(set(keys)) != len(keys)
        or len(set(baseline)) != len(baseline)
        or len(set(ranked)) != len(ranked)
        or set(keys) != set(baseline) | set(ranked)
        or len(baseline) != min(snapshot.sample.k, snapshot.sample.candidate_total)
        or len(ranked) != len(baseline)
    ):
        raise ValueError("Órdenes de la muestra inconsistentes.")
    return snapshot


def label_template(snapshot: Snapshot) -> Labels:
    return Labels(
        snapshot_id=snapshot.snapshot_id,
        labels=[Label(job_key=job.job_key) for job in snapshot.sample.jobs],
    )


def evaluate(snapshot: Snapshot, labels: Labels) -> dict[str, Any]:
    keys = {job.job_key for job in snapshot.sample.jobs}
    verdicts = {label.job_key: label.verdict for label in labels.labels}
    if labels.snapshot_id != snapshot.snapshot_id:
        raise ValueError("Las etiquetas pertenecen a otra muestra.")
    if len(verdicts) != len(labels.labels) or keys != verdicts.keys():
        raise ValueError("Debe haber exactamente una etiqueta por clave de la muestra.")

    def metrics(order: list[str]) -> dict[str, Any]:
        counts = Counter(verdicts[key] for key in order)
        n = len(order)
        unresolved = counts["pending"] + counts["unknown"]
        return {
            "n": n,
            "useful": counts["useful"],
            "not_useful": counts["not_useful"],
            "unknown": counts["unknown"],
            "pending": counts["pending"],
            "precision": counts["useful"] / n if n and not unresolved else None,
            "precision_lower": counts["useful"] / n if n else None,
            "precision_upper": (counts["useful"] + unresolved) / n if n else None,
        }

    baseline = snapshot.sample.list_order
    ranked = [item.job_key for item in snapshot.sample.rank_order]
    list_metrics, rank_metrics = metrics(baseline), metrics(ranked)
    by_source = {
        source: {
            **counts,
            "sample": metrics(
                [job.job_key for job in snapshot.sample.jobs if job.source_id == source]
            ),
        }
        for source, counts in snapshot.sample.source_counts.items()
    }
    return {
        "schema_version": 1,
        "snapshot_id": snapshot.snapshot_id,
        "profile": snapshot.sample.profile.name,
        "k": snapshot.sample.k,
        "candidate_total": snapshot.sample.candidate_total,
        "list": list_metrics,
        "rank": rank_metrics,
        "precision_delta": (
            rank_metrics["precision"] - list_metrics["precision"]
            if rank_metrics["precision"] is not None and list_metrics["precision"] is not None
            else None
        ),
        "useful_only_in_list": [
            key for key in baseline if key not in ranked and verdicts[key] == "useful"
        ],
        "useful_only_in_rank": [
            key for key in ranked if key not in baseline and verdicts[key] == "useful"
        ],
        "sources": by_source,
        "notice": (
            "Precisión sobre n=min(k,candidatos); unknown/pending dejan precisión sin resolver. "
            "Muestra dirigida, no aleatoria: no estima recall ni calidad global de una fuente. "
            "La evaluación incluye descartados en ambos órdenes y no exporta notas personales."
        ),
    }
