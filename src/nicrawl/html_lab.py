"""Muestra acotada del sandbox de hockey; no entra en la colección de empleos."""

import ssl
from dataclasses import asdict, dataclass
from urllib.parse import parse_qs, urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

from nicrawl.acquisition import Clock, SystemClock

HOST = "www.scrapethissite.com"
ROOT = f"https://{HOST}"
PAGE = ROOT + "/pages/forms/"
ROBOTS = ROOT + "/robots.txt"
AGENT = "nicrawl-lab/0.10.0"


class LabError(RuntimeError):
    pass


@dataclass(frozen=True)
class TeamSeason:
    team: str
    year: int
    wins: int


def bounded_get(client: httpx.Client, url: str, limit: int, timeout: int) -> tuple[int, str, bytes]:
    chunks: list[bytes] = []
    size = 0
    with client.stream("GET", url, timeout=timeout, follow_redirects=False) as response:
        for chunk in response.iter_bytes(chunk_size=65536):
            size += len(chunk)
            if size > limit:
                raise LabError("Respuesta supera el límite de bytes.")
            chunks.append(chunk)
        return response.status_code, response.headers.get("content-type", ""), b"".join(chunks)


def checked_page(url: str, page: int) -> bool:
    parts = urlsplit(url)
    return (
        parts.scheme == "https"
        and parts.hostname == HOST
        and parts.port in (None, 443)
        and parts.username is None
        and parts.password is None
        and parts.path == "/pages/forms/"
        and parse_qs(parts.query) == {"page_num": [str(page)]}
    )


def parse_page(body: bytes, page: int) -> tuple[list[TeamSeason], str | None]:
    soup = BeautifulSoup(body, "html.parser")
    table = soup.select_one("table")
    if table is None:
        raise LabError("Falta tabla: la estructura HTML cambió.")
    rows = table.select("tr.team")
    if not 1 <= len(rows) <= 100:
        raise LabError("Cantidad de filas ausente o fuera del límite.")
    found: list[TeamSeason] = []
    for row in rows:
        name = row.select_one("td.name")
        year = row.select_one("td.year")
        wins = row.select_one("td.wins")
        if not name or not year or not wins:
            raise LabError("Fila incompleta; no se publicó una página truncada.")
        try:
            item = TeamSeason(
                name.get_text(" ", strip=True),
                int(year.get_text(strip=True)),
                int(wins.get_text(strip=True)),
            )
        except ValueError as error:
            raise LabError("Año o victorias no numéricas.") from error
        if not item.team or not 1900 <= item.year <= 2100 or not 0 <= item.wins <= 100:
            raise LabError("Fila fuera de invariantes.")
        found.append(item)
    if len({(item.team, item.year) for item in found}) != len(found):
        raise LabError("IDs duplicados dentro de la página.")
    next_url = None
    for link in soup.select("a[href]"):
        url = urljoin(PAGE, str(link["href"]))
        if checked_page(url, page + 1):
            next_url = url
            break
    return found, next_url


def sample(
    *, pages: int = 2, transport: httpx.BaseTransport | None = None, clock: Clock | None = None
) -> dict[str, object]:
    if not 1 <= pages <= 2:
        raise ValueError("El laboratorio admite una o dos páginas.")
    clock = clock or SystemClock()
    with httpx.Client(
        transport=transport,
        verify=ssl.create_default_context(),
        headers={"User-Agent": AGENT},
        follow_redirects=False,
    ) as client:
        try:
            robots_status, _, robots_body = bounded_get(client, ROBOTS, 128 * 1024, 10)
            if robots_status == 200:
                parser = RobotFileParser()
                parser.parse(robots_body.decode("utf-8", errors="replace").splitlines())
                allowed = parser.can_fetch(AGENT, PAGE)
                robots_state = "allowed" if allowed else "disallowed"
            elif robots_status in (404, 410):
                allowed = True
                robots_state = "absent"
            else:
                raise LabError(f"robots.txt no verificable (HTTP {robots_status}).")
            if not allowed:
                raise LabError("robots.txt excluye la ruta del laboratorio.")
            results: list[TeamSeason] = []
            url = PAGE
            visited: set[str] = set()
            has_more = False
            for index in range(1, pages + 1):
                if url in visited or not (url == PAGE if index == 1 else checked_page(url, index)):
                    raise LabError("Paginación repetida o fuera de la ruta aprobada.")
                if robots_status == 200 and not parser.can_fetch(AGENT, url):
                    raise LabError("robots.txt excluye una página.")
                # robots.txt también fue una request al mismo host.
                clock.sleep(2)
                visited.add(url)
                status, media, body = bounded_get(client, url, 1024 * 1024, 15)
                if status != 200:
                    raise LabError(f"Página {index}: HTTP {status}.")
                if media.split(";", 1)[0].lower() != "text/html":
                    raise LabError("La respuesta no es HTML.")
                rows, next_url = parse_page(body, index)
                results.extend(rows)
                has_more = next_url is not None
                if index < pages:
                    if next_url is None:
                        raise LabError("Página siguiente ausente antes del límite solicitado.")
                    url = next_url
            if len({(item.team, item.year) for item in results}) != len(results):
                raise LabError("IDs repetidos entre páginas.")
            return {
                "source": "Scrape This Site / Hockey Teams",
                "robots": robots_state,
                "pages_sampled": pages,
                "rows": len(results),
                "has_more": has_more,
                "sample": [asdict(item) for item in results[:3]],
                "persisted": False,
            }
        except httpx.HTTPError as error:
            raise LabError(f"Fallo de red sin evasión ({type(error).__name__}).") from error
