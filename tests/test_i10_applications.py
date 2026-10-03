import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import pytest
from test_i9_saved import db as base_db
from typer.testing import CliRunner

from nicrawl import applications as a
from nicrawl.agent_tools import AgentTools
from nicrawl.cli import app
from nicrawl.storage import Repository

db = base_db


def manual(**changes):
    return a.Create.model_validate(
        {
            "url": "https://www.linkedin.com/jobs/view/123456?trk=feed",
            "title": "Senior Software Engineer",
            "company": "Empresa ficticia",
            "reason": "Nota privada de seguimiento",
            **changes,
        }
    )


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_reads_and_invalid_inputs_do_not_create_files(tmp_path):
    database = tmp_path / "absent.sqlite3"
    assert a.list_applications(database)["total"] == 0
    with pytest.raises(a.NotFound):
        a.show(database, "missing")
    with pytest.raises(ValueError):
        a.create(database, manual(url="javascript:alert(1)"))
    assert not database.exists() and not a.tracker_path(database).exists()


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "file:///etc/passwd",
        "https://user:pass@example.com/",
        "https://example.com:broken/",
        "https://example.com/\n",
        "https://example.com/a b",
    ],
)
def test_invalid_urls(url):
    with pytest.raises(ValueError):
        a.canonical_url(url)


@pytest.mark.parametrize(
    "changes",
    [
        {"title": " "},
        {"job_key": "remotive:0"},
        {"unknown": True},
        {"state": "submitted"},
    ],
)
def test_invalid_create_contract(changes):
    with pytest.raises(ValueError):
        manual(**changes)


def test_identity_linkedin_variants_and_functional_query_parameters(db):
    first = a.create(db, manual())
    duplicate = a.create(
        db, manual(url="https://linkedin.com/jobs/view/senior-engineer-123456/?refId=x")
    )
    assert duplicate["created"] is False
    assert duplicate["application"]["id"] == first["application"]["id"]
    assert len(duplicate["history"]) == 1
    assert (
        a.canonical_url("https://EXAMPLE.com:443/job?id=1&utm_source=x#top")
        == "https://example.com/job?id=1"
    )
    assert a.canonical_url("https://example.com/job?id=1") != a.canonical_url(
        "https://example.com/job?id=2"
    )
    assert a.create(db, manual(url="https://www.linkedin.com/jobs/view/999"))["created"]


def test_linked_dedup_captures_origin_and_preserves_collection_and_privacy(db):
    before = digest(db)
    result = a.create(db, a.Create(job_key="greenhouse%3Agitlab:0", reason="PRIVATE_APPLICATION"))
    identifier = result["application"]["id"]
    assert result["application"]["job_key"] == "greenhouse%3Agitlab:0"
    assert not a.create(db, a.Create(job_key="greenhouse%3Agitlab:0"))["created"]
    assert not a.create(db, manual(url=result["application"]["url"]))["created"]
    response = AgentTools(db).call("get_job", {"job_key": "greenhouse%3Agitlab:0"})
    assert "PRIVATE_APPLICATION" not in response.model_dump_json()
    assert digest(db) == before
    with closing(Repository(db)) as repo, repo.connection:
        repo.connection.execute("UPDATE jobs SET payload=replace(payload,'Junior','Changed')")
    assert a.show(db, identifier)["application"]["title"] == result["application"]["title"]


def test_update_history_corrections_same_state_and_conflict(db):
    identifier = a.create(db, manual())["application"]["id"]
    for revision, state in enumerate(["submitted", "interview", "closed", "draft", "draft"], 1):
        report = a.update(
            db,
            identifier,
            a.Update(
                state=state,
                expected_revision=revision,
                reason="Registro o corrección explícita",
            ),
        )
        assert report["application"]["revision"] == revision + 1
    assert len(report["history"]) == 6
    assert report["history"][3]["from_state"] == "interview"
    with pytest.raises(a.Conflict):
        a.update(db, identifier, a.Update(state="closed", expected_revision=1, reason="Reintento"))
    assert len(a.show(db, identifier)["history"]) == 6
    assert a.list_applications(db, state="draft")["total"] == 1
    with pytest.raises(ValueError):
        a.Update(state="submitted", expected_revision=True, reason="bad")
    with pytest.raises(ValueError):
        a.Update(state="submitted", expected_revision=6, reason=" ")


def test_event_failure_rolls_back_state(db):
    identifier = a.create(db, manual())["application"]["id"]
    with closing(sqlite3.connect(a.tracker_path(db))) as connection, connection:
        connection.execute(
            "CREATE TRIGGER fail_event BEFORE INSERT ON events "
            "BEGIN SELECT RAISE(ABORT,'test'); END"
        )
    with pytest.raises(sqlite3.IntegrityError):
        a.update(db, identifier, a.Update(state="submitted", expected_revision=1, reason="Enviada"))
    report = a.show(db, identifier)
    assert report["application"]["state"] == "draft" and len(report["history"]) == 1


def test_concurrent_create_and_revision_conflict(db):
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: a.create(db, manual()), range(2)))
    assert sorted(item["created"] for item in results) == [False, True]
    identifier = results[0]["application"]["id"]

    def change(_):
        try:
            a.update(
                db, identifier, a.Update(state="submitted", expected_revision=1, reason="Hecho")
            )
            return "ok"
        except a.Conflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(change, range(2))) == ["conflict", "ok"]
    assert len(a.show(db, identifier)["history"]) == 2


def test_foreign_tracker_is_not_modified(db):
    path = a.tracker_path(db)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("CREATE TABLE foreign_data(x)")
    before = digest(path)
    with pytest.raises(a.ApplicationError):
        a.create(db, manual())
    assert digest(path) == before


def test_cli_end_to_end(db):
    runner = CliRunner()

    def command(*args):
        return runner.invoke(app, ["--db", str(db), "applications", *args])

    created = command("add", "--job-key", "greenhouse%3Agitlab:0")
    assert created.exit_code == 0
    identifier = json.loads(created.output)["application"]["id"]
    assert (
        command(
            "update",
            identifier,
            "--state",
            "submitted",
            "--revision",
            "1",
            "--reason",
            "Envié manualmente",
        ).exit_code
        == 0
    )
    report = json.loads(command("show", identifier).output)
    assert report["application"]["state"] == "submitted"
    assert len(report["history"]) == 2
    assert json.loads(command("list", "--state", "submitted").output)["total"] == 1
