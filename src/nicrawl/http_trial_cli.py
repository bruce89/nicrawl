"""CLI del emisor HTTP y arranque del receptor independiente."""

from typing import Annotated

import typer

from nicrawl import http_trial
from nicrawl.application_cli import _emit
from nicrawl.test_receiver import PORT

app = typer.Typer(help="Ensayo HTTP contra el receptor de prueba local.", no_args_is_help=True)


@app.command("prepare")
def prepare(
    ctx: typer.Context,
    draft_id: str,
    version: Annotated[int, typer.Option(min=1)],
    port: Annotated[int, typer.Option(min=1, max=65535)] = PORT,
) -> None:
    _emit(lambda: http_trial.prepare(ctx.obj, draft_id, version, port))


@app.command("show")
def show(ctx: typer.Context, identifier: str) -> None:
    _emit(lambda: http_trial.show(ctx.obj, identifier))


@app.command("send")
def send(
    ctx: typer.Context,
    identifier: str,
    confirm_sha256: Annotated[str, typer.Option()],
    scenario: str = "accepted",
) -> None:
    _emit(lambda: http_trial.send(ctx.obj, identifier, confirm_sha256, scenario))


@app.command("reconcile")
def reconcile(ctx: typer.Context, identifier: str) -> None:
    _emit(lambda: http_trial.reconcile(ctx.obj, identifier))


@app.command("retry")
def retry(
    ctx: typer.Context, identifier: str, confirm_sha256: Annotated[str, typer.Option()]
) -> None:
    _emit(lambda: http_trial.retry(ctx.obj, identifier, confirm_sha256))
