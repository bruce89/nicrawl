"""Contrato Remotive: validación externa, normalización y conflictos de identidad."""

from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from nicrawl.domain import (
    InvalidCandidate,
    JobCandidate,
    JobDraft,
    Rejection,
    content_hash,
    normalize_job,
    normalize_text,
)

SOURCE = "remotive"
SCOPE = '{"category":"software-dev"}'
ENDPOINT = "https://remotive.com/api/remote-jobs?category=software-dev"
ADAPTER_VERSION = "remotive-1"
NORMALIZER_VERSION = "1"


class SourceFormatError(ValueError):
    pass


class Envelope(BaseModel):
    model_config = ConfigDict(strict=True)
    count: int = Field(alias="job-count", ge=0, le=10_000)
    jobs: list[object] = Field(max_length=10_000)


class RemoteJob(BaseModel):
    model_config = ConfigDict(strict=True)
    id: int | str
    title: str
    company_name: str
    url: str
    description: str | None = None
    candidate_required_location: str | None = None
    salary: str | None = None
    job_type: str | None = None
    tags: list[str] = Field(default_factory=list)
    publication_date: str | None = None


@dataclass(frozen=True)
class SourceBatch:
    candidates: int
    jobs: tuple[JobDraft, ...]
    rejections: tuple[Rejection, ...]
    duplicates: int
    warnings: tuple[str, ...] = ()


def html_text(value: str | None) -> str | None:
    if value is None:
        return None
    soup = BeautifulSoup(value, "html.parser")
    for hidden in soup.select("script, style, template"):
        hidden.decompose()
    for block in soup.select("p, div, li, ul, ol, br, h1, h2, h3, h4, h5, h6"):
        block.insert_before("\n")
        block.insert_after("\n")
    return normalize_text(soup.get_text())


def published_instant(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed.astimezone(UTC).isoformat() if parsed.tzinfo is not None else None


def parse_response(body: bytes) -> SourceBatch:
    try:
        envelope = Envelope.model_validate_json(body)
    except ValidationError as error:
        raise SourceFormatError("JSON o envoltura Remotive inválidos.") from error
    if envelope.count != len(envelope.jobs):
        raise SourceFormatError("job-count no coincide con jobs; colección incompleta.")

    groups: dict[str, list[tuple[int, JobDraft]]] = defaultdict(list)
    rejections: list[Rejection] = []
    invalid_ids: set[str] = set()
    for index, raw in enumerate(envelope.jobs, 1):
        raw_id: str | None = None
        if isinstance(raw, dict) and type(raw.get("id")) in (str, int):
            raw_id = normalize_text(str(raw["id"]))
        try:
            dto = RemoteJob.model_validate(raw)
            if isinstance(dto.id, int) and dto.id <= 0:
                raise InvalidCandidate("id", "ID debe ser positivo.")
            # La API entrega enlaces absolutos: no reparar un enlace truncado con la base.
            if not dto.url.startswith(("https://", "http://")):
                raise InvalidCandidate("url", "El origen debe ser una URL absoluta.")
            draft = normalize_job(
                JobCandidate(
                    str(dto.id),
                    dto.title,
                    dto.company_name,
                    dto.url,
                    html_text(dto.description),
                    dto.candidate_required_location,
                    dto.salary,
                ),
                source_id=SOURCE,
                base_url="https://remotive.com/",
            )
            draft = replace(
                draft,
                work_mode="remote",
                employment_type_raw=normalize_text(dto.job_type),
                tags=tuple(sorted({tag for value in dto.tags if (tag := normalize_text(value))})),
                published_raw=dto.publication_date,
                published_at=published_instant(dto.publication_date),
            )
            groups[draft.source_job_id].append((index, draft))
        except (ValidationError, InvalidCandidate) as error:
            if raw_id:
                invalid_ids.add(raw_id)
            field = (
                error.field
                if isinstance(error, InvalidCandidate)
                else ",".join(
                    ".".join(map(str, item["loc"])) for item in error.errors(include_input=False)
                )
            )
            rejections.append(Rejection(index, raw_id, field, "Registro inválido."))

    jobs: list[JobDraft] = []
    duplicates = 0
    for job_id, entries in groups.items():
        if job_id in invalid_ids or len({content_hash(job) for _, job in entries}) > 1:
            rejections.extend(
                Rejection(index, job_id, "id", "Conflicto de contenido para el mismo ID.")
                for index, _ in entries
            )
        else:
            # La selección es estable incluso si solo difieren fechas no materiales.
            jobs.append(min((job for _, job in entries), key=lambda job: job.published_raw or ""))
            duplicates += len(entries) - 1
    warnings = tuple(
        f"{job.source_job_id}: descripción no informada"
        for job in jobs
        if job.description_text is None
    )
    return SourceBatch(envelope.count, tuple(jobs), tuple(rejections), duplicates, warnings)
