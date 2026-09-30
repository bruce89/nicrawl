"""Board público GitLab en Greenhouse; contrato de una respuesta completa."""

import html
from collections import defaultdict
from dataclasses import replace

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from nicrawl.domain import (
    InvalidCandidate,
    JobCandidate,
    JobDraft,
    Rejection,
    content_hash,
    normalize_job,
)
from nicrawl.sources.remotive import SourceBatch, SourceFormatError, html_text, published_instant

SOURCE = "greenhouse:gitlab"
SCOPE = '{"board":"gitlab","content":true}'
ENDPOINT = "https://boards-api.greenhouse.io/v1/boards/gitlab/jobs?content=true"
ADAPTER_VERSION = "greenhouse-gitlab-1"
BOARD_URL = "https://job-boards.greenhouse.io/gitlab"


class Location(BaseModel):
    model_config = ConfigDict(strict=True)
    name: str


class Post(BaseModel):
    model_config = ConfigDict(strict=True)
    id: int = Field(gt=0)
    title: str
    absolute_url: str
    location: Location
    content: str | None = None
    updated_at: str | None = None
    first_published: str | None = None


class Meta(BaseModel):
    model_config = ConfigDict(strict=True)
    total: int = Field(ge=0, le=10_000)


class Envelope(BaseModel):
    model_config = ConfigDict(strict=True)
    jobs: list[object] = Field(max_length=10_000)
    meta: Meta


def description(value: str | None) -> str | None:
    if value is None:
        return None
    # Greenhouse documenta HTML escapado, que puede venir en dos niveles.
    return html_text(html.unescape(html.unescape(value)))


def parse_response(body: bytes) -> SourceBatch:
    try:
        envelope = Envelope.model_validate_json(body)
    except ValidationError as error:
        raise SourceFormatError("JSON o envoltura Greenhouse inválidos.") from error
    if envelope.meta.total != len(envelope.jobs):
        raise SourceFormatError("meta.total no coincide con jobs; lote incompleto.")

    groups: dict[str, list[tuple[int, JobDraft]]] = defaultdict(list)
    rejections: list[Rejection] = []
    invalid_ids: set[str] = set()
    for index, raw in enumerate(envelope.jobs, 1):
        raw_id = str(raw["id"]) if isinstance(raw, dict) and type(raw.get("id")) is int else None
        try:
            dto = Post.model_validate(raw)
            if not dto.absolute_url.startswith(("https://", "http://")):
                raise InvalidCandidate("absolute_url", "La URL de origen debe ser absoluta.")
            draft = normalize_job(
                JobCandidate(
                    str(dto.id),
                    dto.title,
                    "GitLab",
                    dto.absolute_url,
                    description(dto.content),
                    dto.location.name,
                ),
                source_id=SOURCE,
                base_url=BOARD_URL,
            )
            draft = replace(
                draft,
                work_mode="unknown",
                published_raw=dto.first_published,
                published_at=published_instant(dto.first_published),
                source_updated_at=published_instant(dto.updated_at),
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
            jobs.append(min((job for _, job in entries), key=lambda item: item.published_raw or ""))
            duplicates += len(entries) - 1
    warnings = tuple(
        f"{job.source_job_id}: descripción no informada"
        for job in jobs
        if job.description_text is None
    )
    return SourceBatch(envelope.meta.total, tuple(jobs), tuple(rejections), duplicates, warnings)
