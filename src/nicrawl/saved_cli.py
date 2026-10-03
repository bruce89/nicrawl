"""Presentación CLI de perfiles y evaluación; sin reglas duplicadas."""

import json
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any

import typer

from nicrawl import evaluation, saved_searches
from nicrawl.exporting import export_file
from nicrawl.saved_searches import SavedSearch, read_json
from nicrawl.storage import StorageError

app = typer.Typer(help="Guardar búsquedas y evaluar una muestra fija.", no_args_is_help=True)


def _emit(operation: Callable[[], Any]) -> None:
    try:
        result = operation()
    except (ValueError, OSError, sqlite3.Error, StorageError) as error:
        typer.echo(f"Error local: {error}", err=True)
        raise typer.Exit(1) from error
    typer.echo(json.dumps(result, ensure_ascii=True, indent=2))


@app.command("save")
def save_command(
    ctx: typer.Context,
    name: str,
    goal: str = "",
    view: str = "list",
    query: str = "",
    title_query: str = "",
    company: str = "",
    source: str = "",
    location_text: str = "",
    limit: Annotated[int, typer.Option(min=1, max=200)] = 50,
    want: Annotated[list[str] | None, typer.Option()] = None,
    avoid: Annotated[list[str] | None, typer.Option()] = None,
    mode: str | None = None,
    fields: str = "title,tags,description",
    include_dismissed: bool = False,
    replace: bool = False,
) -> None:
    """Guardar filtros y preferencias; requiere --replace si el nombre ya existe."""

    def execute() -> dict[str, Any]:
        profile = SavedSearch.model_validate(
            {
                "name": name,
                "goal": goal,
                "view": view,
                "query": query,
                "title_query": title_query,
                "company": company,
                "source": "" if source == "all" else source,
                "location_text": location_text,
                "limit": limit,
                "want": [term.strip() for term in want or []],
                "avoid": [term.strip() for term in avoid or []],
                "mode": mode,
                "fields": [part.strip() for part in fields.split(",") if part.strip()],
                "include_dismissed": include_dismissed,
            }
        )
        return saved_searches.save(ctx.obj, profile, replace=replace).model_dump()

    _emit(execute)


@app.command("list")
def list_command(ctx: typer.Context) -> None:
    """Mostrar perfiles de la base seleccionada, sin ejecutar consultas."""
    _emit(lambda: saved_searches.list_saved(ctx.obj).model_dump())


@app.command("show")
def show_command(ctx: typer.Context, name: str) -> None:
    _emit(lambda: saved_searches.get_saved(ctx.obj, name).model_dump())


@app.command("run")
def run_command(ctx: typer.Context, name: str) -> None:
    """Ejecutar list o rank con la configuración guardada."""
    _emit(lambda: saved_searches.run_saved(ctx.obj, name))


@app.command("delete")
def delete_command(ctx: typer.Context, name: str) -> None:
    """Eliminar solo el perfil nombrado, sin borrar ofertas ni notas."""

    def execute() -> dict[str, str]:
        saved_searches.delete(ctx.obj, name)
        return {"deleted": name}

    _emit(execute)


@app.command("snapshot")
def snapshot_command(
    ctx: typer.Context,
    name: str,
    output: Annotated[Path, typer.Option()],
    k: Annotated[int, typer.Option(min=1, max=20)] = 10,
) -> None:
    """Congelar top-k de list y rank sobre una misma instantánea de SQLite."""

    def execute() -> dict[str, Any]:
        snapshot = evaluation.capture(ctx.obj, name, k=k)
        export_file(snapshot.model_dump(), output, format="json", database=ctx.obj)
        return {
            "snapshot_id": snapshot.snapshot_id,
            "sample_size": len(snapshot.sample.jobs),
            "output": str(output),
        }

    _emit(execute)


@app.command("label-template")
def template_command(
    ctx: typer.Context,
    snapshot: Annotated[Path, typer.Option()],
    output: Annotated[Path, typer.Option()],
) -> None:
    """Crear etiquetas pendientes; completar manualmente el archivo resultante."""

    def execute() -> dict[str, str]:
        template = evaluation.label_template(evaluation.load_snapshot(snapshot))
        export_file(template.model_dump(), output, format="json", database=ctx.obj)
        return {"output": str(output)}

    _emit(execute)


@app.command("evaluate")
def evaluate_command(
    snapshot: Annotated[Path, typer.Option()], labels: Annotated[Path, typer.Option()]
) -> None:
    """Comparar órdenes y evidencia por fuente sin consultar la base actual."""
    _emit(
        lambda: evaluation.evaluate(
            evaluation.load_snapshot(snapshot),
            evaluation.Labels.model_validate(read_json(labels)),
        )
    )
