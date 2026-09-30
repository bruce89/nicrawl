"""Experimento reproducible de I/O concurrente: transporte falso, cero SQLite/red real."""

import asyncio
from dataclasses import dataclass, field
from time import perf_counter
from typing import cast

import httpx


@dataclass(frozen=True)
class Feed:
    name: str
    host: str


FEEDS = (Feed("remotive", "remotive.example"), Feed("greenhouse:gitlab", "greenhouse.example"))


@dataclass
class Trace:
    active: int = 0
    peak_active: int = 0
    active_by_host: dict[str, int] = field(default_factory=dict)
    peak_by_host: dict[str, int] = field(default_factory=dict)
    requests: int = 0
    transport_closed: bool = False


class SyntheticTransport(httpx.AsyncBaseTransport):
    """El transporte nunca abre sockets; simula espera cooperativa por host."""

    def __init__(self, delay: float, records: int, trace: Trace) -> None:
        self.delay, self.records, self.trace = delay, records, trace

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host
        self.trace.requests += 1
        self.trace.active += 1
        self.trace.peak_active = max(self.trace.peak_active, self.trace.active)
        self.trace.active_by_host[host] = self.trace.active_by_host.get(host, 0) + 1
        self.trace.peak_by_host[host] = max(
            self.trace.peak_by_host.get(host, 0), self.trace.active_by_host[host]
        )
        try:
            await asyncio.sleep(self.delay)
            return httpx.Response(200, json={"records": list(range(self.records))})
        finally:
            self.trace.active -= 1
            self.trace.active_by_host[host] -= 1

    async def aclose(self) -> None:
        self.trace.transport_closed = True


async def sequential(
    feeds: tuple[Feed, ...], *, delay: float, records: int, write_delay: float
) -> dict[str, object]:
    trace = Trace()
    written: list[tuple[str, int]] = []
    started = perf_counter()
    async with httpx.AsyncClient(transport=SyntheticTransport(delay, records, trace)) as client:
        for feed in feeds:
            response = await client.get(f"https://{feed.host}/sample")
            response.raise_for_status()
            for value in response.json()["records"]:
                await asyncio.sleep(write_delay)
                written.append((feed.name, value))
    return {
        "seconds": round(perf_counter() - started, 4),
        "written": len(written),
        "requests": trace.requests,
        "peak_active": trace.peak_active,
        "transport_closed": trace.transport_closed,
    }


async def parallel(
    feeds: tuple[Feed, ...],
    *,
    delay: float,
    records: int,
    write_delay: float,
    max_in_flight: int = 2,
    queue_size: int = 1,
    cancel_source: str | None = None,
) -> dict[str, object]:
    if not 1 <= max_in_flight <= 2 or not 1 <= queue_size <= 2:
        raise ValueError("El laboratorio limita las requests y la cola a 1–2.")
    if cancel_source is not None and cancel_source not in {feed.name for feed in feeds}:
        raise ValueError("Fuente a cancelar desconocida.")
    if len({feed.name for feed in feeds}) != len(feeds):
        raise ValueError("Los nombres de fuentes deben ser únicos.")
    trace = Trace()
    queue: asyncio.Queue[tuple[str, int] | None] = asyncio.Queue(maxsize=queue_size)
    global_limit = asyncio.Semaphore(max_in_flight)
    host_limits = {feed.host: asyncio.Lock() for feed in feeds}
    written: list[tuple[str, int]] = []
    cancelled: list[str] = []
    queue_peak = 0
    backpressure_events = 0

    async def writer() -> None:
        while True:
            item = await queue.get()
            try:
                if item is None:
                    return
                await asyncio.sleep(write_delay)
                written.append(item)
            finally:
                queue.task_done()

    async def producer(feed: Feed, client: httpx.AsyncClient) -> None:
        nonlocal queue_peak, backpressure_events
        try:
            async with global_limit, host_limits[feed.host]:
                response = await client.get(f"https://{feed.host}/sample")
                response.raise_for_status()
            values = response.json()["records"]
            for value in values:
                if queue.full():
                    backpressure_events += 1
                await queue.put((feed.name, value))
                queue_peak = max(queue_peak, queue.qsize())
        except asyncio.CancelledError:
            cancelled.append(feed.name)
            raise

    started = perf_counter()
    async with httpx.AsyncClient(transport=SyntheticTransport(delay, records, trace)) as client:
        async with asyncio.TaskGroup() as group:
            consumer = group.create_task(writer())
            tasks = {feed.name: group.create_task(producer(feed, client)) for feed in feeds}
            if cancel_source is not None:
                await asyncio.sleep(delay / 2)
                tasks[cancel_source].cancel()
            await asyncio.gather(*tasks.values(), return_exceptions=True)
            await queue.join()
            await queue.put(None)
            await consumer
    return {
        "seconds": round(perf_counter() - started, 4),
        "written": len(written),
        "requests": trace.requests,
        "peak_active": trace.peak_active,
        "peak_by_host": trace.peak_by_host,
        "queue_peak": queue_peak,
        "backpressure_events": backpressure_events,
        "cancelled": sorted(cancelled),
        "written_by_source": {
            feed.name: sum(name == feed.name for name, _ in written) for feed in feeds
        },
        "transport_closed": trace.transport_closed,
    }


async def compare(
    *, delay_ms: int = 200, records: int = 8, write_ms: int = 10
) -> dict[str, object]:
    if not 1 <= delay_ms <= 2000 or not 1 <= records <= 100 or not 0 <= write_ms <= 100:
        raise ValueError("Parámetros fuera del alcance del laboratorio.")
    delay, write_delay = delay_ms / 1000, write_ms / 1000
    baseline = await sequential(FEEDS, delay=delay, records=records, write_delay=write_delay)
    concurrent = await parallel(FEEDS, delay=delay, records=records, write_delay=write_delay)
    cancelled = await parallel(
        FEEDS, delay=delay, records=records, write_delay=write_delay, cancel_source=FEEDS[0].name
    )
    return {
        "mode": "synthetic_no_network_no_database",
        "feeds": [feed.name for feed in FEEDS],
        "delay_ms": delay_ms,
        "records_per_feed": records,
        "write_ms": write_ms,
        "sequential": baseline,
        "concurrent": concurrent,
        "cancellation": cancelled,
        "speedup": round(cast(float, baseline["seconds"]) / cast(float, concurrent["seconds"]), 2),
    }
