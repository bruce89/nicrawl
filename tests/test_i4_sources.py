import json
import sqlite3
from contextlib import closing

import httpx
import pytest
from typer.testing import CliRunner

from nicrawl.cli import app
from nicrawl.collection import collect
from nicrawl.html_lab import PAGE, ROBOTS, LabError, parse_page, sample
from nicrawl.queries import Filters, search
from nicrawl.sources import greenhouse, remotive
from nicrawl.storage import Repository


def post(identifier=1, **changes):
    return {
        "id": identifier,
        "title": "Backend Engineer",
        "absolute_url": f"https://job-boards.greenhouse.io/gitlab/jobs/{identifier}",
        "location": {"name": "Remote, Americas"},
        "content": "&lt;p&gt;Python &amp;amp; SQL&lt;/p&gt;<script>ignore</script>",
        "updated_at": "2026-09-27T12:00:00Z",
        **changes,
    }


def body(*items, total=None):
    return json.dumps(
        {"jobs": items, "meta": {"total": len(items) if total is None else total}}
    ).encode()


@pytest.mark.parametrize(
    "raw",
    [b"[]", b"{}", body(post(), total=2), body(*[post(i) for i in range(10001)]), b"invalid"],
    ids=["list", "missing", "mismatch", "overflow", "invalid"],
)
def test_greenhouse_incomplete_envelope(raw):
    with pytest.raises(remotive.SourceFormatError):
        greenhouse.parse_response(raw)


def test_greenhouse_mapping_and_invalid_conflicts():
    batch = greenhouse.parse_response(
        body(post(), post(2, title=""), post(3, first_published="2026-09-27T10:00:00-03:00"))
    )
    assert batch.candidates == 3 and len(batch.jobs) == 2 and len(batch.rejections) == 1
    assert batch.jobs[0].source_id == "greenhouse:gitlab"
    assert batch.jobs[0].company == "GitLab"
    assert batch.jobs[0].description_text == "Python & SQL"
    assert batch.jobs[0].work_mode == "unknown"
    assert batch.jobs[0].source_updated_at == "2026-09-27T12:00:00+00:00"
    assert batch.jobs[1].published_at == "2026-09-27T13:00:00+00:00"
    conflict = greenhouse.parse_response(body(post(), post(title="Changed"), post(4)))
    assert [item.source_job_id for item in conflict.jobs] == ["4"]
    assert len(conflict.rejections) == 2


def test_greenhouse_same_id_duplicate_and_missing_location():
    batch = greenhouse.parse_response(body(post(), post(), post(3, location=None)))
    assert batch.duplicates == 1 and len(batch.rejections) == 1
    assert len(batch.jobs) == 1


def test_two_sources_independent_policy_and_unified_queries(tmp_path):
    database = tmp_path / "both.sqlite3"
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if "greenhouse" in str(request.url):
            return httpx.Response(
                200, content=body(post()), headers={"content-type": "application/json"}
            )
        return httpx.Response(
            200,
            content=json.dumps(
                {
                    "job-count": 1,
                    "jobs": [
                        {
                            "id": 100,
                            "title": "Python Developer",
                            "company_name": "Company",
                            "url": "https://remotive.com/jobs/100",
                        }
                    ],
                }
            ).encode(),
            headers={"content-type": "application/json"},
        )

    transport = httpx.MockTransport(handler)
    assert collect(database, source_id="remotive", transport=transport).status == "succeeded"
    assert (
        collect(database, source_id="greenhouse:gitlab", transport=transport).status == "succeeded"
    )
    assert len(calls) == 2
    assert (
        collect(database, source_id="greenhouse:gitlab", transport=transport).status == "deferred"
    )
    assert len(calls) == 2
    assert search(database)["total"] == 2
    assert search(database, Filters(source="greenhouse:gitlab"))["total"] == 1
    with closing(Repository(database, readonly=True)) as repo:
        assert repo.status(source="remotive")["jobs"] == 1
        assert repo.status(source="greenhouse:gitlab")["jobs"] == 1
        assert repo.connection.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] == 2
    result = CliRunner().invoke(
        app, ["--db", str(database), "list", "--source", "greenhouse:gitlab"]
    )
    assert result.exit_code == 0 and json.loads(result.output)["total"] == 1


def html_page(page=1, next_page=True, broken=False):
    rows = f"<table><tr class='team'><td class='name'>Ñandú</td><td class='year'>{1989 + page}</td>"
    rows += "" if broken else "<td class='wins'>44</td>"
    rows += "</tr></table>"
    if next_page:
        rows += f"<a href='/pages/forms/?page_num={page + 1}'>next</a>"
    return rows.encode()


class FakeClock:
    def __init__(self):
        self.sleeps = []

    def sleep(self, seconds):
        self.sleeps.append(seconds)

    def now(self):
        raise AssertionError("not used")

    def monotonic(self):
        raise AssertionError("not used")


def test_html_lab_two_pages_and_wait():
    seen = []

    def handler(request):
        seen.append(str(request.url))
        if str(request.url) == ROBOTS:
            return httpx.Response(200, content=b"User-agent: *\nDisallow: /lessons/\n")
        page = 1 if str(request.url) == PAGE else 2
        return httpx.Response(200, content=html_page(page), headers={"content-type": "text/html"})

    clock = FakeClock()
    result = sample(transport=httpx.MockTransport(handler), clock=clock)
    assert result["pages_sampled"] == 2 and result["rows"] == 2
    assert result["persisted"] is False
    assert clock.sleeps == [2, 2]
    assert seen == [ROBOTS, PAGE, PAGE + "?page_num=2"]


@pytest.mark.parametrize(
    "robots,expected",
    [
        (b"User-agent: *\nDisallow: /pages/", "excluye"),
        (b"User-agent: nicrawl-lab\nDisallow: /", "excluye"),
    ],
)
def test_html_lab_robots_denies_before_page(robots, expected):
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, content=robots)

    with pytest.raises(LabError, match=expected):
        sample(transport=httpx.MockTransport(handler))
    assert seen == [ROBOTS]


@pytest.mark.parametrize("status", [301, 403, 429, 500])
def test_html_lab_unverifiable_robots_stops(status):
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(status)

    with pytest.raises(LabError):
        sample(transport=httpx.MockTransport(handler))
    assert seen == [ROBOTS]


def test_html_lab_broken_and_duplicate_page():
    with pytest.raises(LabError, match="incompleta"):
        parse_page(html_page(broken=True), 1)
    with pytest.raises(LabError, match="tabla"):
        parse_page(b"<html>empty</html>", 1)

    def handler(request):
        if str(request.url) == ROBOTS:
            return httpx.Response(404)
        return httpx.Response(200, content=html_page(), headers={"content-type": "text/html"})

    with pytest.raises(LabError, match="repetidos"):
        sample(transport=httpx.MockTransport(handler), clock=FakeClock())


def test_html_lab_oversized_and_foreign_pagination():
    with pytest.raises(LabError, match="límite"):

        def handler(request):
            if str(request.url) == ROBOTS:
                return httpx.Response(404)
            return httpx.Response(
                200, content=b"x" * (1024 * 1024 + 1), headers={"content-type": "text/html"}
            )

        sample(pages=1, transport=httpx.MockTransport(handler))
    foreign = (
        html_page(next_page=False) + b"<a href='https://evil.test/pages/forms/?page_num=2'>2</a>"
    )

    def handler(request):
        if str(request.url) == ROBOTS:
            return httpx.Response(404)
        return httpx.Response(200, content=foreign, headers={"content-type": "text/html"})

    with pytest.raises(LabError, match="siguiente ausente"):
        sample(transport=httpx.MockTransport(handler))


def test_current_database_schema(tmp_path):
    path = tmp_path / "db.sqlite3"
    with closing(Repository(path)):
        pass
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
