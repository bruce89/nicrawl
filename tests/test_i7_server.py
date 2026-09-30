import json
import threading
from contextlib import closing
from datetime import UTC, datetime
from urllib.parse import quote

import httpx
import pytest
from typer.testing import CliRunner

from nicrawl.cli import app
from nicrawl.domain import JobDraft
from nicrawl.server import create_server
from nicrawl.sources.remotive import SourceBatch
from nicrawl.storage import Repository

NOW = datetime(2026, 9, 28, 16, tzinfo=UTC)


@pytest.fixture
def local_api(tmp_path):
    database = tmp_path / "jobs.sqlite3"
    with closing(Repository(database)) as repo:
        for source, identifier, title in (
            ("remotive", "101", "Python Engineer"),
            ("greenhouse:gitlab", "202", "Data Engineer"),
        ):
            run = repo.start_run(NOW, source=source)
            job = JobDraft(
                source,
                identifier,
                title,
                "Ejemplo",
                f"https://example.com/{identifier}",
                "Python y datos",
                "Remote, US",
                None,
                "unknown",
                tags=("Python",),
            )
            repo.publish(run, SourceBatch(1, (job,), (), 0), NOW, {"valid": 1})
    server = create_server(database, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with httpx.Client(
            base_url=f"http://127.0.0.1:{server.server_port}", trust_env=False
        ) as client:
            yield client, database
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_api_list_rank_detail_match_cli(local_api):
    client, database = local_api
    listed = client.get("/api/jobs", params={"source": "greenhouse:gitlab"})
    assert listed.status_code == 200
    api_list = listed.json()
    cli_list = CliRunner().invoke(
        app, ["--db", str(database), "list", "--source", "greenhouse:gitlab"]
    )
    assert cli_list.exit_code == 0, cli_list.output
    assert api_list["jobs"] == json.loads(cli_list.output)["jobs"]
    assert api_list["total"] == 1

    ranked = client.get("/api/rank", params={"want": "Python", "mode": "remote"})
    assert ranked.status_code == 200
    api_rank = ranked.json()
    cli_rank = CliRunner().invoke(
        app, ["--db", str(database), "rank", "--want", "Python", "--mode", "remote"]
    )
    assert cli_rank.exit_code == 0, cli_rank.output
    assert [
        (item["job"]["job_key"], item["score"], item["reasons"]) for item in api_rank["results"]
    ] == [
        (item["job"]["job_key"], item["score"], item["reasons"])
        for item in json.loads(cli_rank.output)["results"]
    ]
    key = "greenhouse%3Agitlab:202"
    detail = client.get("/api/jobs/" + quote(key, safe=""))
    assert detail.status_code == 200
    assert detail.json()["source_status"]["source"] == "greenhouse:gitlab"


def test_personal_patch_preserves_provider_and_cli_can_read(local_api):
    client, database = local_api
    key = "greenhouse%3Agitlab:202"
    url = "/api/jobs/" + quote(key, safe="") + "/personal"
    before = client.get("/api/jobs/" + quote(key, safe="")).json()["job"]
    response = client.patch(url, json={"state": "favorite", "note": "Revisar país"})
    assert response.status_code == 200
    assert response.json()["personal"]["state"] == "favorite"
    cli_show = CliRunner().invoke(app, ["--db", str(database), "show", key])
    assert cli_show.exit_code == 0
    detail = json.loads(cli_show.output)
    assert detail["personal"]["note"] == "Revisar país"
    assert detail["job"] == before
    reset = client.patch(url, json={"state": "unreviewed", "clear_note": True})
    assert reset.status_code == 200 and reset.json()["personal"]["updated_at"] is None


def test_static_assets_headers_and_invalid_requests(local_api):
    client, _database = local_api
    page = client.get("/")
    assert page.status_code == 200 and "nicrawl" in page.text
    assert "default-src 'self'" in page.headers["content-security-policy"]
    assert client.get("/app.js").status_code == 200
    assert client.get("/style.css").status_code == 200
    assert client.get("/api/rank").status_code == 400
    assert client.get("/api/jobs", params={"limit": 201}).status_code == 400
    assert client.get("/api/jobs", params={"unknown": "x"}).status_code == 400
    assert client.get("/api/jobs/remotive:missing").status_code == 404
    assert client.get("/not-found").status_code == 404
    assert client.get("/api/health").json()["status"] == "ok"


def test_write_requires_json_and_same_origin(local_api):
    client, _database = local_api
    url = "/api/jobs/remotive:101/personal"
    assert (
        client.patch(
            url, content="state=favorite", headers={"Content-Type": "text/plain"}
        ).status_code
        == 415
    )
    assert (
        client.patch(
            url, json={"state": "favorite"}, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    assert (
        client.get("/api/health", headers={"Host": "evil.example"}).status_code
        == 403
    )
    assert client.patch(url, json={"unexpected": True}).status_code == 400
    assert client.patch(url, json={"note": "x" * 3000}).status_code == 400
    assert (
        client.patch(
            url, json={"state": "favorite"}, headers={"Origin": str(client.base_url).rstrip("/")}
        ).status_code
        == 200
    )
