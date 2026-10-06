"""Adaptador de terminal del ensayo local I12a."""

from typing import Annotated

import typer

from nicrawl import simulation
from nicrawl.application_cli import _emit

app = typer.Typer(
    help="Ensayo local de recepción; no envía postulaciones reales.", no_args_is_help=True
)


@app.command("prepare")
def prepare(
    ctx: typer.Context, draft_id: str, version: Annotated[int, typer.Option(min=1)]
) -> None:
    """Congelar una revisión y mostrar el material para confirmar."""
    _emit(lambda: simulation.prepare(ctx.obj, draft_id, version))


@app.command("show")
def show(ctx: typer.Context, identifier: str) -> None:
    _emit(lambda: simulation.show(ctx.obj, identifier))


@app.command("send")
def send(
    ctx: typer.Context,
    identifier: str,
    confirm_sha256: Annotated[str, typer.Option()],
    scenario: str = "accepted",
) -> None:
    """Confirmar el hash revisado; accepted/rejected/timeout-before/timeout-after."""
    _emit(lambda: simulation.send(ctx.obj, identifier, confirm_sha256, scenario))


@app.command("reconcile")
def reconcile(ctx: typer.Context, identifier: str) -> None:
    """Consultar el recibo local de un resultado incierto; no reenvía."""
    _emit(lambda: simulation.reconcile(ctx.obj, identifier))
