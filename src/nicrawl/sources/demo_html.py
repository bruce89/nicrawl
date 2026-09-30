"""Parser para el contrato HTML de nuestras fixtures; no es un parser universal."""

import re
from copy import deepcopy
from enum import StrEnum
from importlib.resources import files

from bs4 import BeautifulSoup, Tag

from nicrawl.domain import (
    ExtractionResult,
    InvalidCandidate,
    JobCandidate,
    JobDraft,
    Rejection,
    normalize_job,
)

BASE_URL = "https://jobs.example/"
SOURCE_ID = "demo-html"


class Scenario(StrEnum):
    BASIC = "basic"
    OPTIONAL_FIELDS = "optional-fields"
    UNICODE = "unicode"
    EMPTY = "empty"
    BROKEN_LAYOUT = "broken-layout"


class PageStructureError(ValueError):
    """La página no cumple el contrato; cero resultados sería engañoso."""


def load_scenario(scenario: Scenario) -> str:
    """Leer un recurso instalado; no depende del directorio de ejecución."""
    return files("nicrawl.fixtures").joinpath(f"{scenario.value}.html").read_text(encoding="utf-8")


def _attribute(node: Tag | None, name: str) -> str | None:
    if node is None:
        return None
    value = node.get(name)
    return value if isinstance(value, str) else None


def _text(card: Tag, selector: str) -> str | None:
    node = card.select_one(selector)
    if node is None:
        return None
    # Separar bloques sin insertar espacios alrededor de etiquetas inline:
    # <strong>Python</strong>. debe conservar la puntuación.
    text_node = deepcopy(node)
    for block in text_node.select("p, div, li, ul, ol, br, h1, h2, h3, h4, h5, h6"):
        block.insert_before("\n")
        block.insert_after("\n")
    return text_node.get_text()


def parse_jobs(html: str) -> ExtractionResult:
    """Extraer todas las tarjetas, o fallar si no se puede confiar en la página."""
    soup = BeautifulSoup(html, "html.parser")
    for hidden in soup.select("script, style, template"):
        hidden.decompose()

    pages = soup.select('main[data-page="jobs"]')
    if len(pages) != 1:
        raise PageStructureError("Se esperaba un único contenedor main[data-page=jobs].")
    page = pages[0]
    lists = page.select("[data-job-list]")
    if len(lists) != 1:
        raise PageStructureError("Falta la lista de ofertas o aparece más de una vez.")
    declared_count = _attribute(page, "data-count")
    if declared_count is None or re.fullmatch(r"[0-9]{1,5}", declared_count) is None:
        raise PageStructureError("Falta un data-count válido para verificar la colección.")

    cards = lists[0].select(":scope > article.job")
    if len(cards) != int(declared_count):
        raise PageStructureError(
            "La cantidad de tarjetas no coincide con data-count; revisar layout."
        )
    empty_marker = page.select('[data-empty="true"]')
    if not cards and len(empty_marker) != 1:
        raise PageStructureError("Una lista vacía requiere un marcador explícito data-empty=true.")
    if cards and empty_marker:
        raise PageStructureError("La página declara estar vacía pero contiene ofertas.")

    jobs: list[JobDraft] = []
    rejections: list[Rejection] = []
    for index, card in enumerate(cards, start=1):
        candidate = JobCandidate(
            source_job_id=_attribute(card, "data-id"),
            title=_text(card, "h2 a"),
            company=_text(card, ".company"),
            href=_attribute(card.select_one("h2 a"), "href"),
            description=_text(card, ".description"),
            location=_text(card, ".location"),
            salary=_text(card, ".salary"),
        )
        try:
            jobs.append(normalize_job(candidate, source_id=SOURCE_ID, base_url=BASE_URL))
        except InvalidCandidate as error:
            rejections.append(Rejection(index, candidate.source_job_id, error.field, error.reason))

    return ExtractionResult(len(cards), tuple(jobs), tuple(rejections))
