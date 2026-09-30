from pathlib import Path

import pytest
from typer.testing import CliRunner

from nicrawl.cli import app
from nicrawl.sources.demo_html import Scenario, load_scenario

runner = CliRunner()


@pytest.mark.parametrize(
    ("scenario", "exit_code", "message"),
    [
        ("basic", 3, "Candidatos: 4 | válidos: 3 | rechazados: 1"),
        ("optional-fields", 0, "No informado"),
        ("unicode", 0, "Ñandú & Compañía"),
        ("empty", 0, "Candidatos: 0 | válidos: 0 | rechazados: 0"),
        ("broken-layout", 1, "Error de demo:"),
    ],
)
def test_demo_contract_from_another_directory_without_writes(
    scenario: str, exit_code: int, message: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["demo", "--scenario", scenario])
    assert result.exit_code == exit_code, result.output
    assert message in result.output
    assert list(tmp_path.iterdir()) == []
    if scenario == "basic":
        assert "Advertencia: candidato 4, campo title" in result.stderr
        assert "Advertencia" not in result.stdout
    if scenario == "broken-layout":
        assert result.stdout == ""


def test_invalid_scenario_is_usage_error() -> None:
    result = runner.invoke(app, ["demo", "--scenario", "https://external.example/"])
    assert result.exit_code == 2


def test_untrusted_text_is_plain_and_cannot_control_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    html = load_scenario(Scenario.OPTIONAL_FIELDS).replace(
        "Empresa Mínima", "[bold]Empresa[/bold]\x1b[31m\u202eFIN\x07"
    )
    monkeypatch.setattr("nicrawl.cli.load_scenario", lambda scenario: html)
    result = runner.invoke(app, ["demo"])
    assert result.exit_code == 0
    assert "[bold]Empresa[/bold]FIN" in result.stdout
    assert "\x1b" not in result.stdout
    assert "\u202e" not in result.stdout
    assert "\x07" not in result.stdout


def test_all_invalid_is_failure_not_partial_success(monkeypatch: pytest.MonkeyPatch) -> None:
    html = load_scenario(Scenario.OPTIONAL_FIELDS).replace("Backend Developer", " ")
    monkeypatch.setattr("nicrawl.cli.load_scenario", lambda scenario: html)
    result = runner.invoke(app, ["demo"])
    assert result.exit_code == 1
    assert "válidos: 0 | rechazados: 1" in result.stdout
