import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from nicrawl.acquisition import retry_after
from nicrawl.cli import app
from nicrawl.collection import collect
from nicrawl.locking import CollectionBusy, collection_lock
from nicrawl.sources.remotive import SourceFormatError, parse_response
from nicrawl.storage import Deferred, Repository, StorageError


class FakeClock:
    def __init__(self) -> None:
        self.wall = datetime(2026, 9, 25, 12, tzinfo=UTC)
        self.elapsed = 0.0

    def now(self) -> datetime:
        return self.wall

    def monotonic(self) -> float:
        return self.elapsed

    def sleep(self, seconds: float) -> None:
        self.wall += timedelta(seconds=seconds)
        self.elapsed += seconds


def job(identifier: int = 1, **changes: object) -> dict[str, object]:
    return {
        "id": identifier,
        "title": " Python  Developer ",
        "company_name": "Ñandú & Co",
        "url": f"https://remotive.com/jobs/{identifier}",
        "description": "<p>Usar <strong>C++</strong>.</p><script>ignorar</script>",
        "publication_date": "2026-09-24T10:00:00",
        "salary": "80k; moneda desconocida",
        "candidate_required_location": "US only",
        "tags": ["Python", "SQL", "Python"],
        **changes,
    }


def payload(*jobs: dict[str, object]) -> bytes:
    return json.dumps({"job-count": len(jobs), "jobs": jobs}).encode()


def good_transport(*jobs: dict[str, object]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://remotive.com/api/remote-jobs?category=software-dev"
        return httpx.Response(
            200, content=payload(*jobs), headers={"content-type": "application/json"}
        )

    return httpx.MockTransport(handler)


def rows(path: Path, table: str) -> list[sqlite3.Row]:
    assert table in {"jobs", "runs", "changes", "run_items", "attempts", "source_state"}
    with closing(sqlite3.connect(path)) as connection:
        connection.row_factory = sqlite3.Row
        return connection.execute(f"SELECT * FROM {table}").fetchall()


def test_mapper_preserves_unknowns_and_aware_dates() -> None:
    batch = parse_response(payload(job(), job(2, publication_date="2026-09-24T10:00:00-03:00")))
    assert batch.jobs[0].description_text == "Usar C++."
    assert batch.jobs[0].published_at is None
    assert batch.jobs[0].published_raw == "2026-09-24T10:00:00"
    assert batch.jobs[0].salary_raw == "80k; moneda desconocida"
    assert batch.jobs[0].location_raw == "US only"
    assert batch.jobs[0].tags == ("Python", "SQL")
    assert batch.jobs[1].published_at == "2026-09-24T13:00:00+00:00"


@pytest.mark.parametrize(
    "body",
    [
        b"broken",
        b"[]",
        b'{"jobs":[]}',
        b'{"job-count":1,"jobs":[]}',
        b'{"job-count":true,"jobs":[]}',
        b'{"job-count":10001,"jobs":[]}',
    ],
)
def test_invalid_envelope_does_not_become_empty_success(body: bytes) -> None:
    with pytest.raises(SourceFormatError):
        parse_response(body)


def test_conflicts_reject_all_candidates_with_same_id() -> None:
    batch = parse_response(payload(job(), job(title="Different"), job(2), job(3, title="")))
    assert [item.source_job_id for item in batch.jobs] == ["2"]
    assert len(batch.rejections) == 3
    assert batch.candidates == len(batch.jobs) + len(batch.rejections) + batch.duplicates


def test_exact_duplicates_and_order_are_normalized() -> None:
    batch = parse_response(payload(job(), job(tags=["SQL", "Python"], title="Python Developer")))
    assert len(batch.jobs) == 1
    assert batch.duplicates == 1


def test_invalid_duplicate_does_not_allow_same_id_to_be_published() -> None:
    batch = parse_response(payload(job(), job(title=123)))
    assert batch.jobs == ()
    assert len(batch.rejections) == 2


def test_full_history_idempotence_change_absence_and_offline_status(tmp_path: Path) -> None:
    db = tmp_path / "jobs.sqlite3"
    clock = FakeClock()
    first = collect(db, clock=clock, transport=good_transport(job(), job(2)))
    assert first.status == "succeeded" and first.metrics["new"] == 2
    clock.sleep(12 * 3600)
    second = collect(db, clock=clock, transport=good_transport(job(2), job()))
    assert second.metrics["unchanged"] == 2 and second.metrics["new"] == 0
    assert len(rows(db, "changes")) == 2
    first_seen = rows(db, "jobs")[0]["first_seen_at"]
    clock.sleep(12 * 3600)
    third = collect(db, clock=clock, transport=good_transport(job(title="New title")))
    assert third.metrics["updated"] == 1
    assert len(rows(db, "jobs")) == 2
    assert rows(db, "jobs")[0]["first_seen_at"] == first_seen
    assert rows(db, "jobs")[1]["last_seen_at"] == rows(db, "runs")[1]["finished_at"]
    with closing(Repository(db, readonly=True)) as repo:
        assert repo.status()["jobs"] == 2
    assert len(rows(db, "run_items")) == 5


def test_cooldown_prevents_network_after_reopening(tmp_path: Path) -> None:
    db = tmp_path / "jobs.db"
    clock = FakeClock()
    collect(db, clock=clock, transport=good_transport(job()))
    result = collect(db, clock=clock, transport=good_transport(job(2)))
    assert result.status == "deferred" and result.metrics["attempts"] == 0
    assert len(rows(db, "attempts")) == 1
    assert len(rows(db, "jobs")) == 1


def test_timeout_retries_once_preserves_data(tmp_path: Path) -> None:
    db = tmp_path / "jobs.db"
    clock = FakeClock()
    collect(db, clock=clock, transport=good_transport(job()))
    before = dict(rows(db, "jobs")[0])
    clock.sleep(12 * 3600)
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("simulado", request=request)

    result = collect(db, clock=clock, transport=httpx.MockTransport(handler))
    assert result.status == "failed" and calls == 2
    assert dict(rows(db, "jobs")[0]) == before
    assert len(rows(db, "attempts")) == 3


def test_503_then_success_and_attempts_are_durable_before_request(tmp_path: Path) -> None:
    db = tmp_path / "jobs.db"
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert len(rows(db, "attempts")) == calls
        if calls == 1:
            return httpx.Response(503)
        return httpx.Response(
            200, content=payload(job()), headers={"content-type": "application/json"}
        )

    result = collect(db, clock=FakeClock(), transport=httpx.MockTransport(handler))
    assert result.status == "succeeded" and calls == 2


@pytest.mark.parametrize(
    "header,hours", [("172800", 48), ("Sun, 27 Sep 2026 12:00:00 GMT", 48), ("bad", 24)]
)
def test_429_persists_most_restrictive_cooldown(tmp_path: Path, header: str, hours: int) -> None:
    db = tmp_path / "jobs.db"
    clock = FakeClock()
    result = collect(
        db,
        clock=clock,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(429, headers={"retry-after": header})
        ),
    )
    assert result.status == "deferred" and result.metrics["attempts"] == 1
    until = datetime.fromisoformat(rows(db, "source_state")[0]["next_allowed_at"])
    assert until == clock.now() + timedelta(hours=hours)
    clock.sleep(13 * 3600)
    assert collect(db, clock=clock, transport=good_transport(job())).status == "deferred"
    assert len(rows(db, "attempts")) == 1


@pytest.mark.parametrize(
    "status,body,content_type",
    [(403, b"", "text/plain"), (200, b"<html>captcha</html>", "text/html")],
)
def test_blocked_source_is_durable(
    tmp_path: Path, status: int, body: bytes, content_type: str
) -> None:
    db = tmp_path / "jobs.db"
    clock = FakeClock()
    result = collect(
        db,
        clock=clock,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                status, content=body, headers={"content-type": content_type}
            )
        ),
    )
    assert result.status == "failed"
    assert rows(db, "source_state")[0]["disabled_reason"]
    clock.sleep(48 * 3600)
    result = collect(db, clock=clock, transport=good_transport(job()))
    assert result.status == "failed" and result.metrics["attempts"] == 0


def test_partial_and_all_invalid(tmp_path: Path) -> None:
    db = tmp_path / "jobs.db"
    clock = FakeClock()
    result = collect(db, clock=clock, transport=good_transport(job(), job(2, title="")))
    assert result.status == "partial"
    assert rows(db, "runs")[0]["coverage"] == "incomplete"
    clock.sleep(12 * 3600)
    result = collect(db, clock=clock, transport=good_transport(job(2, title="")))
    assert result.status == "failed"
    assert len(rows(db, "jobs")) == 1


def test_sql_failure_rolls_back_all_changes(tmp_path: Path) -> None:
    db = tmp_path / "jobs.db"
    clock = FakeClock()
    collect(db, clock=clock, transport=good_transport(job()))
    before = dict(rows(db, "jobs")[0])
    with closing(sqlite3.connect(db)) as connection:
        connection.execute(
            "CREATE TRIGGER fail_second BEFORE INSERT ON jobs "
            "WHEN NEW.source_job_id='2' BEGIN SELECT RAISE(ABORT,'test failure'); END"
        )
        connection.commit()
    clock.sleep(12 * 3600)
    result = collect(db, clock=clock, transport=good_transport(job(title="changed"), job(2)))
    assert result.status == "failed"
    assert dict(rows(db, "jobs")[0]) == before
    assert len(rows(db, "changes")) == len(rows(db, "run_items")) == 1


def test_recovery_and_exclusive_lock(tmp_path: Path) -> None:
    db = tmp_path / "jobs.db"
    clock = FakeClock()
    with collection_lock(db):
        with closing(Repository(db)) as repo:
            old = repo.start_run(clock.now())
        with pytest.raises(CollectionBusy):
            collect(db, clock=clock, transport=good_transport(job()))
    result = collect(db, clock=clock, transport=good_transport(job()))
    assert result.status == "succeeded"
    assert rows(db, "runs")[0]["run_id"] == old
    assert rows(db, "runs")[0]["status"] == "interrupted"


def test_size_limit_and_foreign_redirect_never_publish(tmp_path: Path) -> None:
    result = collect(
        tmp_path / "size.db", clock=FakeClock(), transport=good_transport(job()), max_bytes=10
    )
    assert result.status == "failed"

    def redirect(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "remotive.com"
        return httpx.Response(302, headers={"location": "https://other.example/jobs"})

    result = collect(
        tmp_path / "redirect.db", clock=FakeClock(), transport=httpx.MockTransport(redirect)
    )
    assert result.status == "failed" and result.metrics["attempts"] == 1


def test_quota_clock_rollback_and_foreign_database(tmp_path: Path) -> None:
    db = tmp_path / "quota.db"
    clock = FakeClock()
    with collection_lock(db), closing(Repository(db)) as repo:
        run_id = repo.start_run(clock.now())
        for number in range(4):
            repo.reserve_attempt(run_id, clock.now(), first=number == 0)
            clock.sleep(60)
        with pytest.raises(Deferred, match="agotada"):
            repo.reserve_attempt(run_id, clock.now(), first=False)
        clock.wall -= timedelta(days=1)
        with pytest.raises(Deferred, match="retrocedió"):
            repo.gate(clock.now())
    foreign = tmp_path / "foreign.db"
    with closing(sqlite3.connect(foreign)) as connection:
        connection.execute("CREATE TABLE unrelated(id INTEGER)")
        connection.commit()
    with pytest.raises(StorageError, match="ajena"):
        Repository(foreign)


def test_status_does_not_create_missing_database_and_cli_source_validation(tmp_path: Path) -> None:
    db = tmp_path / "missing.db"
    result = CliRunner().invoke(app, ["--db", str(db), "status"])
    assert result.exit_code == 1 and not db.exists()
    result = CliRunner().invoke(app, ["--db", str(db), "collect", "--source", "unknown"])
    assert result.exit_code == 2 and not db.exists()


def test_long_retry_after_and_deadline(tmp_path: Path) -> None:
    result = collect(
        tmp_path / "retry.db",
        clock=FakeClock(),
        transport=httpx.MockTransport(
            lambda request: httpx.Response(503, headers={"retry-after": "3600"})
        ),
    )
    assert result.status == "deferred" and result.metrics["attempts"] == 1
    clock = FakeClock()

    def slow(request: httpx.Request) -> httpx.Response:
        clock.sleep(121)
        return httpx.Response(
            200, content=payload(job()), headers={"content-type": "application/json"}
        )

    result = collect(tmp_path / "slow.db", clock=clock, transport=httpx.MockTransport(slow))
    assert result.status == "failed"
    assert retry_after("-5", clock.now()) is None
    assert retry_after("9" * 100, clock.now()) is None
