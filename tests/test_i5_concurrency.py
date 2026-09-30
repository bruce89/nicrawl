import asyncio
import json
from contextlib import closing
from datetime import UTC, datetime, timedelta

import pytest
from typer.testing import CliRunner

from nicrawl.cli import app
from nicrawl.collection import RunResult
from nicrawl.concurrency_lab import FEEDS, Feed, SyntheticTransport, compare, parallel, sequential
from nicrawl.planning import plan
from nicrawl.storage import Repository


def test_concurrent_two_hosts_single_writer_and_backpressure():
    async def scenario():
        baseline = await sequential(FEEDS, delay=0.05, records=12, write_delay=0.008)
        concurrent = await parallel(FEEDS, delay=0.05, records=12, write_delay=0.008)
        assert baseline["written"] == concurrent["written"] == 24
        assert baseline["peak_active"] == 1
        assert concurrent["peak_active"] == 2
        assert concurrent["peak_by_host"] == {"remotive.example": 1, "greenhouse.example": 1}
        assert concurrent["queue_peak"] == 1
        assert concurrent["backpressure_events"] > 0
        assert baseline["transport_closed"] and concurrent["transport_closed"]

    asyncio.run(scenario())


def test_same_host_serializes_and_global_limit_two():
    feeds = (Feed("a", "same.example"), Feed("b", "same.example"), Feed("c", "other.example"))
    result = asyncio.run(parallel(feeds, delay=0.03, records=2, write_delay=0.002, max_in_flight=2))
    assert result["requests"] == 3 and result["written"] == 6
    assert result["peak_active"] <= 2
    assert result["peak_by_host"]["same.example"] == 1
    assert result["queue_peak"] <= 1


def test_cancel_one_source_other_completes_and_transport_closes():
    result = asyncio.run(
        parallel(FEEDS, delay=0.08, records=3, write_delay=0.005, cancel_source="remotive")
    )
    assert result["cancelled"] == ["remotive"]
    assert result["written_by_source"] == {"remotive": 0, "greenhouse:gitlab": 3}
    assert result["transport_closed"]


def test_parent_cancellation_propagates_and_resources_close(monkeypatch):
    closed = []
    original = SyntheticTransport.aclose

    async def aclose(self):
        closed.append(True)
        await original(self)

    monkeypatch.setattr(SyntheticTransport, "aclose", aclose)

    async def scenario():
        task = asyncio.create_task(parallel(FEEDS, delay=0.3, records=3, write_delay=0.01))
        await asyncio.sleep(0.02)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    assert closed == [True]


def test_invalid_limits_and_cancel_source():
    with pytest.raises(ValueError):
        asyncio.run(parallel(FEEDS, delay=0.01, records=1, write_delay=0, queue_size=0))
    with pytest.raises(ValueError):
        asyncio.run(parallel(FEEDS, delay=0.01, records=1, write_delay=0, cancel_source="unknown"))
    with pytest.raises(ValueError):
        asyncio.run(compare(delay_ms=0))


def test_plan_disabled_cooldown_quota_and_missing_database(tmp_path):
    db = tmp_path / "jobs.sqlite3"
    now = datetime(2026, 9, 28, 12, tzinfo=UTC)
    with pytest.raises(Exception, match="No hay base"):
        plan(db, now=now)
    with closing(Repository(db)) as repo:
        run = repo.start_run(now - timedelta(hours=2))
        repo.reserve_attempt(run, now - timedelta(hours=2), first=True)
    report = plan(db, now=now)
    assert report["sources"]["remotive"]["state"] == "deferred"
    assert report["sources"]["greenhouse:gitlab"]["state"] == "uninitialized"
    assert report["sources"]["remotive"]["ready_at"] == (now + timedelta(hours=10)).isoformat()
    with closing(Repository(db)) as repo:
        repo.disable("manual")
    assert plan(db, now=now)["sources"]["remotive"]["state"] == "disabled"
    with closing(Repository(db)) as repo:
        repo.connection.execute("UPDATE source_state SET disabled_reason=NULL,next_allowed_at=NULL")
        for minutes in (30, 29, 28, 27):
            repo.connection.execute(
                "INSERT INTO attempts(run_id,source_id,attempted_at) VALUES(?,?,?)",
                (run, "remotive", (now - timedelta(minutes=minutes)).isoformat()),
            )
        repo.connection.commit()
    result = plan(db, now=now)["sources"]["remotive"]
    assert result["state"] == "deferred"
    assert result["ready_at"] == (now + timedelta(hours=22)).isoformat()


def test_plan_read_only_does_not_change_database(tmp_path):
    db = tmp_path / "jobs.sqlite3"
    with closing(Repository(db)):
        pass
    before = db.read_bytes()
    result = CliRunner().invoke(app, ["--db", str(db), "plan"])
    assert result.exit_code == 0
    assert json.loads(result.output)["sources"]["remotive"]["state"] == "uninitialized"
    assert db.read_bytes() == before


def test_collect_all_continues_after_source_failure_and_reports_codes(monkeypatch, tmp_path):
    called = []

    def fake(database, *, source_id):
        called.append(source_id)
        status = "failed" if source_id == "remotive" else "succeeded"
        return RunResult(source_id, status, status, {})

    monkeypatch.setattr("nicrawl.cli.collect_jobs", fake)
    result = CliRunner().invoke(app, ["--db", str(tmp_path / "missing.db"), "collect-all"])
    assert result.exit_code == 1
    assert called == ["remotive", "greenhouse:gitlab"]
    assert json.loads(result.output)["results"]["greenhouse:gitlab"]["status"] == "succeeded"
    assert not (tmp_path / "missing.db").exists()


def test_lab_cli_no_network_or_database(tmp_path):
    db = tmp_path / "never.sqlite3"
    result = CliRunner().invoke(
        app,
        [
            "--db",
            str(db),
            "lab-concurrency",
            "--delay-ms",
            "15",
            "--records",
            "3",
            "--write-ms",
            "2",
        ],
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["mode"] == "synthetic_no_network_no_database"
    assert report["concurrent"]["written"] == 6
    assert report["cancellation"]["cancelled"] == ["remotive"]
    assert not db.exists()
