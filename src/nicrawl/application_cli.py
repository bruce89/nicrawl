"""CLI para registrar decisiones propias; nunca envía una candidatura."""

import json
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any

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


# Borradores vinculados a una candidatura y a una versión del perfil.
drafts_app = typer.Typer(help="Crear, revisar y exportar borradores locales.", no_args_is_help=True)
app.add_typer(drafts_app, name="draft")


@drafts_app.command("create")
def draft_create(
    ctx: typer.Context,
    application_id: str,
    profile_version: Annotated[int, typer.Option(min=1)],
    claim_id: Annotated[list[str] | None, typer.Option("--claim-id")] = None,
    opening: Annotated[str, typer.Option()] = "",
    question: Annotated[list[str] | None, typer.Option("--question")] = None,
) -> None:
    _emit(
        lambda: applications.create_draft(
            ctx.obj,
            application_id,
            applications.DraftInput(
                profile_version=profile_version,
                claim_ids=claim_id or [],
                opening=opening,
                questions=question or [],
            ),
        )
    )


@drafts_app.command("list")
def draft_list(ctx: typer.Context, application_id: str) -> None:
    _emit(lambda: applications.list_drafts(ctx.obj, application_id))


@drafts_app.command("show")
def draft_show(
    ctx: typer.Context, draft_id: str, version: Annotated[int | None, typer.Option(min=1)] = None
) -> None:
    _emit(lambda: applications.show_draft(ctx.obj, draft_id, version))


@drafts_app.command("revise")
def draft_revise(
    ctx: typer.Context,
    draft_id: str,
    expected_version: Annotated[int, typer.Option(min=1)],
    profile_version: Annotated[int, typer.Option(min=1)],
    claim_id: Annotated[list[str] | None, typer.Option("--claim-id")] = None,
    opening: Annotated[str, typer.Option()] = "",
    question: Annotated[list[str] | None, typer.Option("--question")] = None,
) -> None:
    _emit(
        lambda: applications.revise_draft(
            ctx.obj,
            draft_id,
            expected_version,
            applications.DraftInput(
                profile_version=profile_version,
                claim_ids=claim_id or [],
                opening=opening,
                questions=question or [],
            ),
        )
    )


@drafts_app.command("export")
def draft_export(
    ctx: typer.Context,
    draft_id: str,
    output: Annotated[Path, typer.Option("--output")],
    version: Annotated[int | None, typer.Option(min=1)] = None,
) -> None:
    _emit(lambda: {"exported": str(applications.export_draft(ctx.obj, draft_id, output, version))})
