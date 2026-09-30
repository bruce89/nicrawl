"""Único dueño de retries, presupuesto HTTP y descarga acotada."""

import random
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Protocol
from urllib.parse import urljoin, urlsplit

import httpx

from nicrawl.sources.remotive import ENDPOINT, SourceFormatError
from nicrawl.storage import Deferred, Repository


class Clock(Protocol):
    def now(self) -> datetime: ...
    def monotonic(self) -> float: ...
    def sleep(self, seconds: float) -> None: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)

    def monotonic(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


@dataclass
class FetchStats:
    attempts: int = 0
    bytes_received: int = 0
    http_status: int | None = None


class FetchError(RuntimeError):
    pass


def redirect_target(current: str, location: str | None) -> str:
    return checked_redirect(current, location, allowed_host="remotive.com")


def checked_redirect(current: str, location: str | None, *, allowed_host: str) -> str:
    try:
        if not location or any(character.isspace() for character in location) or "\\" in location:
            raise ValueError("Location inválido")
        target = urljoin(current, location)
        parts = urlsplit(target)
        if (
            parts.scheme != "https"
            or parts.hostname != allowed_host
            or parts.port not in (None, 443)
            or parts.username is not None
            or parts.password is not None
        ):
            raise ValueError("origen no aprobado")
        return target
    except ValueError as error:
        raise FetchError("Redirección inválida o fuera del origen permitido.") from error


def retry_after(value: str | None, now: datetime) -> datetime | None:
    if value is None:
        return None
    try:
        if value.isascii() and value.isdigit():
            return now + timedelta(seconds=int(value))
        date = parsedate_to_datetime(value)
        if date.tzinfo is None:
            return None
        return max(now, date.astimezone(UTC))
    except ValueError, TypeError, OverflowError:
        return None


def fetch(
    client: httpx.Client,
    repository: Repository,
    run_id: str,
    clock: Clock,
    stats: FetchStats,
    *,
    deadline: float,
    max_bytes: int = 10 * 1024 * 1024,
    jitter: float | None = None,
    endpoint: str = ENDPOINT,
    source: str = "remotive",
    allowed_host: str = "remotive.com",
) -> bytes:
    url = endpoint
    retries = 0
    redirects = 0
    while True:
        remaining = deadline - clock.monotonic()
        if remaining <= 0:
            raise FetchError("Se agotó el presupuesto de 120 segundos.")
        repository.reserve_attempt(run_id, clock.now(), first=stats.attempts == 0, source=source)
        stats.attempts += 1
        timeout = httpx.Timeout(
            min(15, remaining),
            connect=min(5, remaining),
            write=min(5, remaining),
            pool=min(5, remaining),
        )
        delay = 2 + (random.random() if jitter is None else jitter)
        try:
            with client.stream("GET", url, timeout=timeout, follow_redirects=False) as response:
                stats.http_status = response.status_code
                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("location")
                    target = checked_redirect(url, location, allowed_host=allowed_host)
                    if redirects >= 3:
                        raise FetchError("Demasiadas redirecciones.")
                    redirects += 1
                    url = target
                    continue
                if response.status_code in (401, 403):
                    repository.disable(
                        f"HTTP {response.status_code}; revisar acceso antes de habilitar.",
                        source=source,
                    )
                    raise FetchError("La fuente rechazó el acceso y quedó detenida para revisión.")
                until = retry_after(response.headers.get("retry-after"), clock.now())
                if response.status_code == 429:
                    until = until or clock.now() + timedelta(hours=24)
                    repository.cooldown(until, source=source)
                    raise Deferred(f"HTTP 429; cooldown hasta al menos {until.isoformat()}.")
                if response.status_code in (502, 503, 504):
                    if until:
                        repository.cooldown(until, source=source)
                        delay = max(delay, (until - clock.now()).total_seconds())
                        if delay >= deadline - clock.monotonic():
                            raise Deferred(
                                f"HTTP {response.status_code}; espera hasta {until.isoformat()}."
                            )
                    if retries >= 1:
                        raise FetchError(
                            f"HTTP {response.status_code} después del reintento permitido."
                        )
                elif response.status_code != 200:
                    raise FetchError(f"HTTP {response.status_code}; no es una colección válida.")
                else:
                    chunks: list[bytes] = []
                    size = 0
                    for chunk in response.iter_bytes(chunk_size=65536):
                        size += len(chunk)
                        stats.bytes_received += len(chunk)
                        if size > max_bytes:
                            raise FetchError("Documento supera 10 MiB descomprimidos.")
                        if stats.bytes_received > 25 * 1024 * 1024:
                            raise FetchError("Lote supera 25 MiB descomprimidos.")
                        if clock.monotonic() >= deadline:
                            raise FetchError("Deadline agotado durante descarga.")
                        chunks.append(chunk)
                    body = b"".join(chunks)
                    media = response.headers.get("content-type", "").split(";", 1)[0].lower()
                    if media != "application/json":
                        if b"captcha" in body[:8192].lower() or b"challenge" in body[:8192].lower():
                            repository.disable(
                                "Desafío recibido; requiere revisión de acceso.", source=source
                            )
                        raise SourceFormatError("Se esperaba application/json, no otra página.")
                    return body
        except (httpx.TimeoutException, httpx.NetworkError) as error:
            if retries >= 1:
                raise FetchError(
                    f"Red fallida tras dos intentos ({type(error).__name__})."
                ) from error
        except httpx.HTTPError as error:
            raise FetchError(f"Fallo HTTP no reintentable ({type(error).__name__}).") from error
        if delay >= deadline - clock.monotonic():
            raise FetchError("No queda presupuesto para reintentar.")
        clock.sleep(delay)
        retries += 1
