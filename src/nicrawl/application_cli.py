"""CLI para registrar decisiones propias; nunca envía una candidatura."""

import json
import sqlite3
from collections.abc import Callable
from typing import Any

import typer

from nicrawl import applications
from nicrawl.storage import StorageError

app = typer.Typer(help="Seguimiento personal de candidaturas, sin envíos.", no_args_is_help=True)


def _emit(operation: Callable[[], dict[str, Any]]) -> None:
    try:
        result = operation()
    except (ValueError, OSError, sqlite3.Error, StorageError) as error:
        typer.echo(f"Error local: {error}", err=True)
        raise typer.Exit(1) from error
    typer.echo(json.dumps(result, ensure_ascii=True, indent=2))


@app.command("add")
def add_command(
    ctx: typer.Context,
    job_key: str | None = None,
    url: str | None = None,
    title: str | None = None,
    company: str | None = None,
    reason: str = "",
) -> None:
    """Crear borrador desde --job-key o referencia --url/--title/--company."""
    _emit(
        lambda: applications.create(
            ctx.obj,
            applications.Create(
                job_key=job_key,
                url=url,
                title=title,
                company=company,
                reason=reason,
            ),
        )
    )


@app.command("list")
def list_command(ctx: typer.Context, state: str = "", limit: int = 50) -> None:
    _emit(lambda: applications.list_applications(ctx.obj, state=state, limit=limit))


@app.command("show")
def show_command(ctx: typer.Context, application_id: str) -> None:
    _emit(lambda: applications.show(ctx.obj, application_id))


@app.command("update")
def update_command(
    ctx: typer.Context,
    application_id: str,
    state: str = typer.Option(...),
    revision: int = typer.Option(...),
    reason: str = typer.Option(...),
) -> None:
    """Registrar estado/motivo; revision evita sobrescribir una edición concurrente."""
    _emit(
        lambda: applications.update(
            ctx.obj,
            application_id,
            applications.Update.model_validate(
                {
                    "state": state,
                    "expected_revision": revision,
                    "reason": reason,
                }
            ),
        )
    )
