"""Entrada y presentación. El parser nunca escribe en la terminal."""

import asyncio
import json
import re
import sqlite3
import sys
import unicodedata
import webbrowser
from contextlib import closing
from enum import StrEnum
from importlib.metadata import version
from io import TextIOWrapper
from pathlib import Path
from typing import Annotated

import typer

from nicrawl import queries
from nicrawl.application_cli import app as applications_app
from nicrawl.collection import collect as collect_jobs
from nicrawl.concurrency_lab import compare as compare_concurrency
from nicrawl.exporting import export_file
from nicrawl.html_lab import LabError
from nicrawl.html_lab import sample as sample_html
from nicrawl.http_trial_cli import app as http_trial_app
from nicrawl.locking import CollectionBusy
from nicrawl.personal import Preferences
from nicrawl.personal import mark as mark_job
from nicrawl.personal import rank as rank_jobs
from nicrawl.planning import plan as plan_sources
from nicrawl.profile_cli import app as profile_app
from nicrawl.saved_cli import app as saved_app
from nicrawl.server import HOST, create_server
from nicrawl.simulation_cli import app as simulation_app
from nicrawl.sources.demo_html import PageStructureError, Scenario, load_scenario, parse_jobs
from nicrawl.storage import Repository, StorageError
from nicrawl.test_receiver import create_receiver

app = typer.Typer(
    help="nicrawl — ofertas locales, ranking explicable y laboratorios de scraping.",
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode=None,
    pretty_exceptions_enable=False,
)
app.add_typer(saved_app, name="saved")
app.add_typer(applications_app, name="applications")
app.add_typer(profile_app, name="profile")
app.add_typer(simulation_app, name="simulation")
app.add_typer(http_trial_app, name="http-trial")


@app.command("test-receiver")
def test_receiver_command(
    ctx: typer.Context,
    port: Annotated[int, typer.Option(min=1, max=65535)] = 8766,
) -> None:
    """Iniciar receptor HTTP de prueba en loopback; detener con Ctrl+C."""
    try:
        with create_receiver(ctx.obj, port) as server:
            typer.echo(f"Receptor de ensayo en http://127.0.0.1:{port}. Ctrl+C para detener.")
            server.serve_forever()
    except KeyboardInterrupt:
        typer.echo("Receptor de ensayo detenido.")
    except (OSError, ValueError, sqlite3.Error) as error:
        typer.echo(f"Error local: {error}", err=True)
        raise typer.Exit(1) from error


def run() -> None:
    """Emitir UTF-8 también al redirigir la salida desde Windows."""
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, TextIOWrapper) and not stream.isatty():
            stream.reconfigure(encoding="utf-8", errors="replace")
    app()


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"nicrawl {version('nicrawl')}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    version_option: Annotated[
        bool,
        typer.Option(
            "--version", callback=_version_callback, is_eager=True, help="Mostrar versión."
        ),
    ] = False,
    db: Annotated[
        Path, typer.Option("--db", help="Base local; ruta relativa al directorio actual.")
    ] = Path("data/nicrawl.sqlite3"),
) -> None:
    """Configurar el grupo sin efectuar I/O de negocio."""
    ctx.obj = db.resolve()


def terminal_text(value: str | None) -> str:
    """Representación de una línea; el modelo conserva el texto original."""
    if value is None:
        return "No informado"
    # Retirar secuencias ANSI completas antes de quitar otros controles.
    without_ansi = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", value)
    return " ".join(
        "".join(
            character
            for character in without_ansi
            if not unicodedata.category(character).startswith("C")
        ).split()
    )


@app.command()
def demo(
    scenario: Annotated[
        Scenario, typer.Option(help="Escenario sintético integrado; nunca descarga una URL.")
    ] = Scenario.BASIC,
) -> None:
    """Extraer ofertas de HTML local y explicar los registros rechazados."""
    try:
        result = parse_jobs(load_scenario(scenario))
    except (PageStructureError, OSError, UnicodeError) as error:
        typer.echo(f"Error de demo: {terminal_text(str(error))}", err=True)
        raise typer.Exit(1) from error

    typer.echo(f"Fuente: demo-html | red: no | escenario: {scenario.value}")
    typer.echo(
        f"Candidatos: {result.candidates} | válidos: {len(result.jobs)} "
        f"| rechazados: {len(result.rejections)}"
    )
    typer.echo("Los datos son ficticios y no se guardaron en ninguna base de datos.")
    for job in result.jobs:
        typer.echo(f"\n{terminal_text(job.source_job_id)} | {terminal_text(job.title)}")
        typer.echo(f"  Empresa: {terminal_text(job.company)}")
        typer.echo(f"  Ubicación declarada: {terminal_text(job.location_raw)}")
        typer.echo(f"  Salario: {terminal_text(job.salary_raw)}")
        typer.echo(f"  Descripción: {terminal_text(job.description_text)}")
        typer.echo(f"  Origen: {terminal_text(job.source_url)}")
    for rejection in result.rejections:
        typer.echo(
            f"Advertencia: candidato {rejection.candidate_index}, "
            f"campo {rejection.field}: {terminal_text(rejection.reason)}",
            err=True,
        )
    if result.rejections:
        # Todos inválidos es un fallo; solo un subconjunto inválido es parcial.
        raise typer.Exit(3 if result.jobs else 1)


class Source(StrEnum):
    REMOTIVE = "remotive"
    GREENHOUSE_GITLAB = "greenhouse:gitlab"


class QuerySource(StrEnum):
    REMOTIVE = "remotive"
    GREENHOUSE_GITLAB = "greenhouse:gitlab"
    ALL = "all"


@app.command("collect")
def collect_command(
    ctx: typer.Context,
    source: Annotated[Source, typer.Option(help="Fuente habilitada.")] = Source.REMOTIVE,
) -> None:
    """Recolectar software-dev respetando cuota durable y publicar en SQLite."""
    database: Path = ctx.obj
    try:
        result = (
            collect_jobs(database)
            if source == Source.REMOTIVE
            else collect_jobs(database, source_id=source.value)
        )
    except KeyboardInterrupt:
        typer.echo("Recolección interrumpida.", err=True)
        raise typer.Exit(130) from None
    except (CollectionBusy, StorageError, sqlite3.Error, OSError) as error:
        typer.echo(f"Error de recolección: {terminal_text(str(error))}", err=True)
        raise typer.Exit(1) from error
    label = (
        "Remotive | ámbito: software-dev"
        if source == Source.REMOTIVE
        else "Greenhouse/GitLab | board: gitlab"
    )
    typer.echo(f"Base: {database}\nFuente: {label} | run: {result.run_id}")
    typer.echo(f"Estado: {result.status} | {terminal_text(result.message)}")
    typer.echo(json.dumps(result.metrics, ensure_ascii=True, indent=2))
    typer.echo(
        "Origen: "
        + (
            "Remotive — https://remotive.com/remote-jobs/software-dev"
            if source == Source.REMOTIVE
            else "GitLab vía Greenhouse — https://job-boards.greenhouse.io/gitlab"
        )
    )
    typer.echo("Cada oferta guarda su source_url original en la base; no se republican avisos.")
    raise typer.Exit({"succeeded": 0, "partial": 3, "deferred": 4, "failed": 1}[result.status])


@app.command()
def status(
    ctx: typer.Context,
    source: Annotated[
        Source, typer.Option(help="Fuente a inspeccionar sin red.")
    ] = Source.REMOTIVE,
) -> None:
    """Mostrar base, colección, última corrida y política. Solo lectura, sin red."""
    database: Path = ctx.obj
    try:
        with closing(Repository(database, readonly=True)) as repository:
            report = repository.status(source=source.value)
    except (StorageError, sqlite3.Error, OSError) as error:
        typer.echo(f"Error de estado: {terminal_text(str(error))}", err=True)
        raise typer.Exit(1) from error
    typer.echo(json.dumps(report, ensure_ascii=True, indent=2))


@app.command("serve")
def serve_command(
    ctx: typer.Context,
    port: Annotated[int, typer.Option(min=1, max=65535, help="Puerto HTTP local.")] = 8765,
    open_browser: Annotated[
        bool, typer.Option("--open/--no-open", help="Abrir la UI en el navegador.")
    ] = True,
) -> None:
    """Iniciar UI y API locales en 127.0.0.1; Ctrl+C para detener."""
    try:
        with closing(Repository(ctx.obj, readonly=True)):
            pass
        server = create_server(ctx.obj, port)
    except (StorageError, sqlite3.Error, OSError, ValueError) as error:
        typer.echo(f"Error del servidor local: {terminal_text(str(error))}", err=True)
        raise typer.Exit(1) from error
    address = f"http://{HOST}:{server.server_port}/"
    typer.echo(f"nicrawl local: {address} · Ctrl+C para detener")
    try:
        if open_browser:
            webbrowser.open(address)
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        typer.echo("Servidor detenido.")
    finally:
        server.server_close()


@app.command("mcp")
def mcp_command(
    ctx: typer.Context,
    max_calls: Annotated[int, typer.Option(min=1, max=1000)] = 100,
) -> None:
    """Servir tres herramientas de lectura por stdio (requiere extra agents)."""
    try:
        from nicrawl.mcp_server import create_mcp_server
    except ModuleNotFoundError as error:
        typer.echo("Instalá el extra: uv sync --locked --extra agents.", err=True)
        raise typer.Exit(1) from error
    try:
        with closing(Repository(ctx.obj, readonly=True)):
            pass
        create_mcp_server(ctx.obj, max_calls=max_calls).run(transport="stdio")
    except (StorageError, sqlite3.Error, OSError, ValueError) as error:
        typer.echo(f"Error MCP local: {terminal_text(str(error))}", err=True)
        raise typer.Exit(1) from error


@app.command("agent-demo")
def agent_demo_command(
    ctx: typer.Context,
    local: Annotated[
        bool, typer.Option(help="Leer la base --db; por defecto usa datos ficticios.")
    ] = False,
) -> None:
    """Probar cliente y servidor MCP por stdio, sin LLM ni API key."""
    try:
        from nicrawl.agent_demo import run_demo
    except ModuleNotFoundError as error:
        typer.echo("Instalá el extra: uv sync --locked --extra agents.", err=True)
        raise typer.Exit(1) from error
    try:
        result = asyncio.run(run_demo(ctx.obj, local=local))
    except Exception as error:
        typer.echo(
            "No se completó la demo MCP; revisá base, extra agents y salida de error.", err=True
        )
        raise typer.Exit(1) from error
    typer.echo(json.dumps(result, ensure_ascii=True, indent=2))


@app.command("plan")
def plan_command(ctx: typer.Context) -> None:
    """Estimar oportunidades de ambas fuentes sin red ni escritura."""
    try:
        report = plan_sources(ctx.obj)
    except (StorageError, sqlite3.Error, OSError, ValueError) as error:
        typer.echo(f"Error del plan: {terminal_text(str(error))}", err=True)
        raise typer.Exit(1) from error
    typer.echo(json.dumps(report, ensure_ascii=True, indent=2))


@app.command("collect-all")
def collect_all(ctx: typer.Context) -> None:
    """Recolectar las dos fuentes en secuencia usando sus cuotas existentes."""
    results: dict[str, object] = {}
    statuses: list[str] = []
    try:
        for source in (Source.REMOTIVE, Source.GREENHOUSE_GITLAB):
            result = collect_jobs(ctx.obj, source_id=source.value)
            results[source.value] = {
                "run_id": result.run_id,
                "status": result.status,
                "message": result.message,
                "metrics": result.metrics,
            }
            statuses.append(result.status)
    except KeyboardInterrupt:
        typer.echo("Recolección conjunta interrumpida.", err=True)
        raise typer.Exit(130) from None
    except (CollectionBusy, StorageError, sqlite3.Error, OSError) as error:
        typer.echo(f"Error de recolección: {terminal_text(str(error))}", err=True)
        raise typer.Exit(1) from error
    typer.echo(
        json.dumps({"database": str(ctx.obj), "results": results}, ensure_ascii=True, indent=2)
    )
    code = (
        1
        if "failed" in statuses
        else 3
        if "partial" in statuses
        else 4
        if "deferred" in statuses
        else 0
    )
    raise typer.Exit(code)


@app.command("lab-concurrency")
def lab_concurrency(
    delay_ms: Annotated[
        int, typer.Option(min=1, max=2000, help="Latencia sintética por request, en milisegundos.")
    ] = 200,
    records: Annotated[
        int, typer.Option(min=1, max=100, help="Registros ficticios por fuente.")
    ] = 8,
    write_ms: Annotated[
        int, typer.Option(min=0, max=100, help="Tiempo de escritura ficticia por registro.")
    ] = 10,
) -> None:
    """Comparar secuencial, dos tareas y cancelación sin red ni SQLite."""
    try:
        report = asyncio.run(
            compare_concurrency(delay_ms=delay_ms, records=records, write_ms=write_ms)
        )
    except (ValueError, OSError) as error:
        typer.echo(f"Error del laboratorio: {terminal_text(str(error))}", err=True)
        raise typer.Exit(1) from error
    typer.echo(json.dumps(report, ensure_ascii=True, indent=2))


@app.command("lab-html")
def lab_html(
    pages: Annotated[int, typer.Option(min=1, max=2, help="Páginas del sandbox; máximo dos.")] = 2,
) -> None:
    """Practicar robots, DOM y paginación acotada sin escribir ofertas."""
    try:
        result = sample_html(pages=pages)
    except (LabError, OSError, ValueError) as error:
        typer.echo(f"Error del laboratorio: {terminal_text(str(error))}", err=True)
        raise typer.Exit(1) from error
    typer.echo(json.dumps(result, ensure_ascii=True, indent=2))


Query = Annotated[str, typer.Option(help="Subcadena en título, empresa o descripción (casefold).")]
Company = Annotated[str, typer.Option(help="Subcadena de empresa; se combina con AND.")]
Location = Annotated[str, typer.Option(help="Restricción geográfica declarada; no elegibilidad.")]
Limit = Annotated[
    int, typer.Option(min=1, max=200, help="Máximo de resultados; total siempre visible.")
]


def _read_error(error: Exception) -> None:
    typer.echo(f"Error local: {terminal_text(str(error))}", err=True)
    raise typer.Exit(1) from error


@app.command("list")
def list_command(
    ctx: typer.Context,
    query: Query = "",
    title_query: Query = "",
    company: Company = "",
    source: QuerySource = QuerySource.ALL,
    location_text: Location = "",
    limit: Limit = 20,
) -> None:
    """Buscar offline. JSON seguro; stale indica observación de hace más de siete días."""
    try:
        report = queries.search(
            ctx.obj,
            queries.Filters(
                query,
                company,
                "" if source == QuerySource.ALL else source,
                location_text,
                title_query,
            ),
            limit=limit,
        )
    except (StorageError, sqlite3.Error, OSError, ValueError) as error:
        _read_error(error)
    else:
        typer.echo(json.dumps(report, ensure_ascii=True, indent=2))


@app.command("show")
def show_command(ctx: typer.Context, job_key: str) -> None:
    """Detalle offline por identidad completa, por ejemplo remotive:123."""
    try:
        report = queries.show(ctx.obj, job_key)
    except (StorageError, sqlite3.Error, OSError, ValueError) as error:
        _read_error(error)
    else:
        typer.echo(json.dumps(report, ensure_ascii=True, indent=2))


class PersonalState(StrEnum):
    UNREVIEWED = "unreviewed"
    FAVORITE = "favorite"
    DISMISSED = "dismissed"


class WorkMode(StrEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


@app.command("mark")
def mark_command(
    ctx: typer.Context,
    job_key: str,
    state: Annotated[PersonalState | None, typer.Option(help="Estado personal.")] = None,
    note: Annotated[str | None, typer.Option(help="Nota local; reemplaza la anterior.")] = None,
    clear_note: Annotated[bool, typer.Option(help="Eliminar la nota local.")] = False,
) -> None:
    """Guardar favorito, descarte o nota sin modificar el aviso de origen."""
    try:
        report = mark_job(
            ctx.obj,
            job_key,
            state=state.value if state else None,
            note=note,
            clear_note=clear_note,
        )
    except (StorageError, sqlite3.Error, OSError, ValueError) as error:
        _read_error(error)
    else:
        typer.echo(json.dumps(report, ensure_ascii=True, indent=2))


@app.command("rank")
def rank_command(
    ctx: typer.Context,
    want: Annotated[list[str] | None, typer.Option(help="Término deseado; repetir opción.")] = None,
    avoid: Annotated[
        list[str] | None, typer.Option(help="Término a evitar; repetir opción.")
    ] = None,
    mode: Annotated[WorkMode | None, typer.Option(help="Modalidad deseada.")] = None,
    fields: Annotated[
        str, typer.Option(help="Reglas de texto activas, separadas por coma.")
    ] = "title,tags,description",
    query: Query = "",
    title_query: Query = "",
    company: Company = "",
    source: QuerySource = QuerySource.ALL,
    location_text: Location = "",
    limit: Limit = 20,
    include_dismissed: Annotated[
        bool, typer.Option(help="Incluir ofertas descartadas en el ranking.")
    ] = False,
) -> None:
    """Ordenar ofertas offline con puntos y razones por regla explícita."""
    try:
        report = rank_jobs(
            ctx.obj,
            Preferences(
                tuple(term.strip() for term in (want or ())),
                tuple(term.strip() for term in (avoid or ())),
                mode.value if mode else None,
                tuple(part.strip() for part in fields.split(",") if part.strip()),
            ),
            filters=queries.Filters(
                query,
                company,
                "" if source == QuerySource.ALL else source,
                location_text,
                title_query,
            ),
            limit=limit,
            include_dismissed=include_dismissed,
        )
    except (StorageError, sqlite3.Error, OSError, ValueError) as error:
        _read_error(error)
    else:
        typer.echo(json.dumps(report, ensure_ascii=True, indent=2))


@app.command("changes")
def changes_command(
    ctx: typer.Context, run: str = "latest", source: Source = Source.REMOTIVE, limit: Limit = 20
) -> None:
    """Altas y diferencias de la última corrida publicada o de --run ID."""
    try:
        report = queries.changes(ctx.obj, run=run, source=source, limit=limit)
    except (StorageError, sqlite3.Error, OSError, ValueError) as error:
        _read_error(error)
    else:
        typer.echo(json.dumps(report, ensure_ascii=True, indent=2))


class ExportFormat(StrEnum):
    JSON = "json"
    CSV = "csv"


@app.command("export")
def export_command(
    ctx: typer.Context,
    output: Annotated[Path, typer.Option(help="Archivo destino local.")],
    format: ExportFormat = ExportFormat.JSON,
    query: Query = "",
    title_query: Query = "",
    company: Company = "",
    source: QuerySource = QuerySource.ALL,
    location_text: Location = "",
    limit: Annotated[
        int | None, typer.Option(min=1, help="Tope opcional; por defecto todos los coincidentes.")
    ] = None,
    overwrite: Annotated[
        bool, typer.Option(help="Reemplazar el destino al completar la escritura.")
    ] = False,
) -> None:
    """Exportar la misma selección que list. CSV protege celdas con prefijos de fórmula."""
    try:
        report = queries.search(
            ctx.obj,
            queries.Filters(
                query,
                company,
                "" if source == QuerySource.ALL else source,
                location_text,
                title_query,
            ),
            limit=limit,
        )
        export_file(report, output, format=format, overwrite=overwrite, database=ctx.obj)
    except (StorageError, sqlite3.Error, OSError, ValueError) as error:
        _read_error(error)
    else:
        typer.echo(
            f"Exportadas {len(report['jobs'])} de {report['total']} ofertas a "
            f"{terminal_text(str(output.absolute()))}. Fuente: {source.value}.",
            err=True,
        )
