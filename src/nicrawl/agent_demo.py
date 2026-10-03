"""Cliente MCP de demostración: proceso real por stdio, sin modelo ni red externa."""

import sys
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import anyio
from mcp import Client
from mcp.client.stdio import StdioServerParameters

from nicrawl.agent_tools import TOOL_NAMES, AgentResponse
from nicrawl.domain import JobDraft
from nicrawl.personal import mark
from nicrawl.sources.remotive import SourceBatch
from nicrawl.storage import Repository


def create_demo_database(database: Path) -> None:
    """Solo invocar con una ruta temporal nueva; no usar la colección personal."""
    if database.exists():
        raise ValueError("La base de demo debe ser nueva.")
    now = datetime(2026, 9, 30, tzinfo=UTC)
    with closing(Repository(database)) as repo:
        for source, identifier, title, location, mode in (
            ("remotive", "demo-101", "Python Developer", "LATAM", "remote"),
            ("greenhouse:gitlab", "demo-202", "Python Data Engineer", "Remote, US", "unknown"),
            ("remotive", "demo-303", "Mobile Developer", None, "unknown"),
        ):
            job = JobDraft(
                source,
                identifier,
                title,
                "Empresa ficticia",
                f"https://jobs.example/{identifier}",
                ("Python y datos. " if identifier != "demo-303" else "Swift e iOS. ")
                + "Consultar requisitos de contratación con el empleador.",
                location,
                None,
                mode,
                tags=("Python",),
            )
            run = repo.start_run(now, source=source)
            repo.publish(run, SourceBatch(1, (job,), (), 0), now, {"valid": 1})
    mark(database, "remotive:demo-101", note="NOTA_PRIVADA_DEMO_NO_EXPORTAR")


async def exercise(database: Path) -> dict[str, Any]:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "nicrawl", "--db", str(database.resolve()), "mcp", "--max-calls", "4"],
        env={"PYTHONUTF8": "1"},
    )
    # La demo tiene plazo y secuencia finitos; el servidor no invoca un LLM.
    with anyio.fail_after(30):
        async with Client(parameters, read_timeout_seconds=10, cache=None) as client:
            definitions = await client.list_tools()
            names = sorted(tool.name for tool in definitions.tools)
            if names != sorted(TOOL_NAMES):
                raise RuntimeError("El servidor no expone el contrato esperado.")

            async def call(name: str, request: dict[str, Any]) -> AgentResponse:
                result = await client.call_tool(name, {"request": request})
                if result.is_error:
                    raise RuntimeError(f"Falló {name}; revisar argumentos y base desde la CLI.")
                return AgentResponse.model_validate(result.structured_content)

            search = await call("search_jobs", {"query": "Python", "limit": 5})
            ranking = await call(
                "rank_jobs",
                {
                    "query": "Python",
                    "want": ["Python"],
                    "mode": "remote",
                    "include_dismissed": True,
                    "limit": 5,
                },
            )
            details = [
                (await call("get_job", {"job_key": item.job.job_key})).model_dump()
                for item in ranking.items[:2]
            ]
            return {
                "demo": "Cliente MCP controlado; no usa un modelo ni interpreta lenguaje natural.",
                "question": "Cinco ofertas Python y qué restricciones de ubicación revisar.",
                "tools": names,
                "search": search.model_dump(),
                "ranking": ranking.model_dump(),
                "details": details,
                "next_step": (
                    "Revisar location_raw, descripción y fuente; unknown no confirma elegibilidad."
                ),
            }


async def run_demo(database: Path, *, local: bool = False) -> dict[str, Any]:
    if local:
        return await exercise(database)
    with TemporaryDirectory(prefix="nicrawl-agent-demo-") as directory:
        fixture = Path(directory) / "synthetic.sqlite3"
        create_demo_database(fixture)
        result = await exercise(fixture)
        result["data"] = "Datos ficticios en base temporal eliminada al cerrar la demo."
        return result
