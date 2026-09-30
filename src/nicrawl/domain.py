"""Modelos inmutables y normalización pura, sin dependencias de HTML o CLI."""

import hashlib
import json
from dataclasses import asdict, dataclass
from urllib.parse import urljoin, urlsplit


@dataclass(frozen=True)
class JobCandidate:
    source_job_id: str | None
    title: str | None
    company: str | None
    href: str | None
    description: str | None = None
    location: str | None = None
    salary: str | None = None


@dataclass(frozen=True)
class JobDraft:
    """Dato normalizado; los tiempos de observación pertenecen al repositorio."""

    source_id: str
    source_job_id: str
    title: str
    company: str
    source_url: str
    description_text: str | None
    location_raw: str | None
    salary_raw: str | None
    work_mode: str = "unknown"
    employment_type_raw: str | None = None
    tags: tuple[str, ...] = ()
    published_raw: str | None = None
    published_at: str | None = None
    source_updated_at: str | None = None


def material_json(job: JobDraft) -> str:
    data = asdict(job)
    for field in ("published_raw", "published_at", "source_updated_at"):
        data.pop(field)
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_hash(job: JobDraft) -> str:
    return hashlib.sha256(material_json(job).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Rejection:
    candidate_index: int
    source_job_id: str | None
    field: str
    reason: str


@dataclass(frozen=True)
class ExtractionResult:
    candidates: int
    jobs: tuple[JobDraft, ...]
    rejections: tuple[Rejection, ...]


class InvalidCandidate(ValueError):
    def __init__(self, field: str, reason: str) -> None:
        self.field = field
        self.reason = reason
        super().__init__(reason)


def normalize_text(value: str | None) -> str | None:
    """Colapsar espacios sin quitar acentos, signos ni restricciones."""
    if value is None:
        return None
    return " ".join(value.split()) or None


def required_text(value: str | None, field: str, label: str) -> str:
    normalized = normalize_text(value)
    if normalized is None:
        raise InvalidCandidate(field, f"falta {label}.")
    return normalized


def normalize_job(candidate: JobCandidate, *, source_id: str, base_url: str) -> JobDraft:
    """Validar invariantes antes de construir el modelo de aplicación."""
    job_id = required_text(candidate.source_job_id, "source_job_id", "ID")
    title = required_text(candidate.title, "title", "título")
    company = required_text(candidate.company, "company", "empresa")
    href = required_text(candidate.href, "source_url", "enlace")
    try:
        # Comprobar el texto original: urlsplit puede descartar ciertos controles.
        if (
            candidate.href is None
            or any(ord(character) < 32 or ord(character) == 127 for character in candidate.href)
            or any(character.isspace() for character in candidate.href.strip())
        ):
            raise ValueError("espacios o controles en el enlace")
        reference = urlsplit(href)
        if (reference.scheme or href.startswith("//")) and not reference.netloc:
            raise ValueError("enlace absoluto sin host")
        url = urljoin(base_url, href)
        parts = urlsplit(url)
        if (
            parts.scheme not in {"https", "http"}
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
            or "\\" in url
        ):
            raise ValueError("URL no admitida")
        _ = parts.port  # Valida también puertos fuera de rango.
    except ValueError as error:
        raise InvalidCandidate("source_url", "enlace HTTP(S) inválido.") from error

    return JobDraft(
        source_id=source_id,
        source_job_id=job_id,
        title=title,
        company=company,
        source_url=url,
        description_text=normalize_text(candidate.description),
        location_raw=normalize_text(candidate.location),
        salary_raw=normalize_text(candidate.salary),
    )
