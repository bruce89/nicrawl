import json
import os
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import httpx
import pytest
from test_collection import FakeClock, good_transport, job, rows
from typer.testing import CliRunner

from nicrawl.cli import app
from nicrawl.collection import collect
from nicrawl.locking import CollectionBusy
from nicrawl.storage import Repository


@pytest.mark.parametrize(
    "status,body,media",
    [
        (200, b"<html>Error</html>", "text/html"),
        (200, b"not-json", "application/json"),
        (404, b"", "application/json"),
        (304, b"", "application/json"),
        (503, b"", "application/json"),
    ],
)
def test_invalid_http_preserves_existing_collection(
    tmp_path: Path,
    status: int,
    body: bytes,
    media: str,
) -> None:
    db = tmp_path / "test.db"
    clock = FakeClock()
    collect(db, clock=clock, transport=good_transport(job()))
    before = dict(rows(db, "jobs")[0])
    clock.sleep(12 * 3600)
    result = collect(
        db,
        clock=clock,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status, content=body, headers={"content-type": media})
        ),
    )
    assert result.status == "failed"
    assert dict(rows(db, "jobs")[0]) == before


@pytest.mark.parametrize("location", ["https://[broken", "https://remotive.com:99999/a", "/a b"])
def test_malformed_redirect_is_recorded_as_failure(tmp_path: Path, location: str) -> None:
    db = tmp_path / "test.db"
    result = collect(
        db,
        clock=FakeClock(),
        transport=httpx.MockTransport(
            lambda request: httpx.Response(302, headers={"location": location})
        ),
    )
    assert result.status == "failed"
    assert rows(db, "runs")[0]["status"] == "failed"


def test_redirect_loop_is_bounded_by_durable_minute_budget(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    result = collect(
        db,
        clock=FakeClock(),
        transport=httpx.MockTransport(
            lambda request: httpx.Response(302, headers={"location": "/api/remote-jobs"})
        ),
    )
    assert result.status == "deferred" and result.metrics["attempts"] == 2
    assert len(rows(db, "jobs")) == 0


def test_valid_empty_warns_about_drop_and_does_not_delete_jobs(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    clock = FakeClock()
    collect(db, clock=clock, transport=good_transport(job()))
    clock.sleep(12 * 3600)
    result = collect(db, clock=clock, transport=good_transport())
    assert result.status == "succeeded"
    assert "80%" in str(result.metrics["warnings"])
    assert len(rows(db, "jobs")) == 1


def test_keyboard_interrupt_is_recorded_and_lock_released(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    clock = FakeClock()

    def handler(request: httpx.Request) -> httpx.Response:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        collect(db, clock=clock, transport=httpx.MockTransport(handler))
    assert rows(db, "runs")[0]["status"] == "interrupted"
    assert collect(db, clock=clock, transport=good_transport()).status == "deferred"


def test_second_process_cannot_collect_and_crash_releases_lock(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    script = """
import os, sys
from pathlib import Path
from datetime import datetime, UTC
from contextlib import closing
from nicrawl.locking import collection_lock
from nicrawl.storage import Repository
with collection_lock(Path(sys.argv[1])), closing(Repository(Path(sys.argv[1]))) as repo:
    now = datetime(2026, 9, 25, 12, tzinfo=UTC)
    run_id = repo.start_run(now)
    repo.reserve_attempt(run_id, now, first=True)
    print("ready", flush=True)
    sys.stdin.readline()
    os._exit(7)
"""
    with subprocess.Popen(
        [sys.executable, "-c", script, str(db)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONUTF8": "1"},
    ) as child:
        try:
            assert child.stdout is not None
            assert child.stdout.readline().strip() == "ready"
            with pytest.raises(CollectionBusy):
                collect(db, clock=FakeClock(), transport=good_transport())
            child.communicate("\n", timeout=15)
            assert child.returncode == 7
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=10)
    clock = FakeClock()
    clock.sleep(13 * 3600)
    result = collect(db, clock=clock, transport=good_transport(job()))
    assert result.status == "succeeded"
    assert rows(db, "runs")[0]["status"] == "interrupted"
    assert len(rows(db, "attempts")) == 2


@pytest.mark.parametrize("partial,expected", [(False, 0), (True, 3)])
def test_cli_collect_status_and_deferred_exit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    partial: bool,
    expected: int,
) -> None:
    db = tmp_path / "test.db"
    clock = FakeClock()
    jobs = [job(), job(2, title="")] if partial else [job()]
    monkeypatch.setattr(
        "nicrawl.cli.collect_jobs",
        lambda path: collect(path, clock=clock, transport=good_transport(*jobs)),
    )
    runner = CliRunner()
    result = runner.invoke(app, ["--db", str(db), "collect"])
    assert result.exit_code == expected, result.output
    assert "Remotive" in result.stdout
    result = runner.invoke(app, ["--db", str(db), "status"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["jobs"] == 1
    result = runner.invoke(app, ["--db", str(db), "collect"])
    assert result.exit_code == 4


def test_source_metadata_changes_do_not_create_material_events(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    clock = FakeClock()
    collect(db, clock=clock, transport=good_transport(job()))
    clock.sleep(12 * 3600)
    result = collect(
        db, clock=clock, transport=good_transport(job(publication_date="2026-09-25T10:00:00+00:00"))
    )
    assert result.metrics["unchanged"] == 1
    assert len(rows(db, "changes")) == 1
    with closing(Repository(db, readonly=True)) as repo:
        assert repo.connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
