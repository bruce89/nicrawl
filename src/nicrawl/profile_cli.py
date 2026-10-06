"""CLI para versiones locales del perfil; no imprime el CV completo por defecto."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any

import typer

from nicrawl import applications

app = typer.Typer(help="Perfiles locales versionados para borradores.", no_args_is_help=True)


def _show(operation: Callable[[], dict[str, Any]], *, include_cv: bool = False) -> None:
    try:
        result = operation()
    except (ValueError, OSError) as error:
        typer.echo(f"Error local: {error}", err=True)
        raise typer.Exit(1) from error
    if isinstance(result, dict) and not include_cv:
        result = {key: value for key, value in result.items() if key != "cv_text"}
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@app.command("save")
def save(
    ctx: typer.Context,
    cv_file: Annotated[Path, typer.Option(exists=True, readable=True)],
    label: Annotated[str, typer.Option()],
    statement: Annotated[list[str], typer.Option()],
    evidence: Annotated[list[str], typer.Option()],
) -> None:
    """Crear una versión. Repetir --statement y --evidence en pares."""
    if len(statement) != len(evidence):
        raise typer.BadParameter("Cada --statement requiere su --evidence correspondiente.")
    try:
        cv = cv_file.read_text(encoding="utf-8-sig")
        request = applications.ProfileInput(
            label=label,
            cv_text=cv,
            claims=[
                applications.ClaimInput(statement=s, evidence=e)
                for s, e in zip(statement, evidence, strict=True)
            ],
        )
    except (OSError, UnicodeError, ValueError) as error:
        typer.echo(f"Error local: {error}", err=True)
        raise typer.Exit(1) from error
    _show(lambda: applications.save_profile(ctx.obj, request))


@app.command("list")
def list_profiles(ctx: typer.Context) -> None:
    _show(lambda: applications.list_profiles(ctx.obj))


@app.command("show")
def show_profile(
    ctx: typer.Context,
    version: Annotated[int, typer.Argument()],
    include_cv: bool = typer.Option(False, "--include-cv"),
) -> None:
    _show(lambda: applications.get_profile(ctx.obj, version), include_cv=include_cv)
