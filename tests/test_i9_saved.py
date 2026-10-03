import hashlib
import json
from contextlib import closing
from datetime import UTC, datetime

import pytest
from typer.testing import CliRunner

from nicrawl import evaluation, queries, saved_searches
from nicrawl.cli import app
from nicrawl.domain import JobDraft
from nicrawl.exporting import export_file
from nicrawl.locking import collection_lock
from nicrawl.personal import mark, rank
from nicrawl.saved_searches import SavedSearch, book_path
from nicrawl.sources.remotive import SourceBatch
from nicrawl.storage import Repository

NOW = datetime(2026, 9, 30, tzinfo=UTC)


@pytest.fixture
def db(tmp_path):
    database = tmp_path / "jobs.sqlite3"
    with closing(Repository(database)) as repo:
        for source, titles in (
            ("remotive", ["Senior Software Engineer", "Software Engineer"]),
            ("greenhouse:gitlab", ["Junior Software Engineer", "Senior Software Engineer"]),
        ):
            jobs = tuple(
                JobDraft(
                    source,
                    str(index),
                    title,
                    "Ejemplo",
                    f"https://jobs.example/{index}",
                    "Texto externo; requisitos por verificar.",
                    None,
                    None,
                    "unknown",
                    tags=(),
                )
                for index, title in enumerate(titles)
            )
            run = repo.start_run(NOW, source=source)
            repo.publish(run, SourceBatch(2, jobs, (), 0), NOW, {"valid": 2})
    mark(database, "remotive:0", note="PRIVATE_NOT_FOR_EVALUATION", state="dismissed")
    saved_searches.save(
        database,
        SavedSearch(
            name="senior-uy",
            view="rank",
            query="Software",
            want=["Senior"],
            goal="Remoto desde Uruguay o presencial en Uruguay",
            limit=2,
        ),
    )
    return database


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_saved_roundtrip_collision_replace_delete_and_readonly(db):
    before = digest(db)
    profile = saved_searches.get_saved(db, "senior-uy")
    expected = rank(db, profile.preferences(), filters=profile.filters(), limit=2)
    actual = saved_searches.run_saved(db, profile.name)
    assert actual["results"] == expected["results"]
    with pytest.raises(ValueError, match="replace"):
        saved_searches.save(db, profile)
    profile.view = "list"
    saved_searches.save(db, profile, replace=True)
    assert (
        saved_searches.run_saved(db, profile.name)["jobs"]
        == queries.search(db, profile.filters(), limit=2)["jobs"]
    )
    saved_searches.delete(db, profile.name)
    assert saved_searches.list_saved(db).searches == []
    assert digest(db) == before


@pytest.mark.parametrize(
    "invalid",
    [
        {"name": "../oops"},
        {"name": "UPPER"},
        {"limit": True},
        {"limit": 201},
        {"query": "x" * 121},
        {"source": "linkedin"},
        {"view": "rank"},
        {"want": ["Senior", "senior"]},
        {"fields": ["title", "title"]},
        {"shell": "x"},
    ],
)
def test_strict_profile(invalid):
    with pytest.raises(ValueError):
        SavedSearch.model_validate({"name": "example", **invalid})


def test_no_side_effects_on_read_and_corrupt_store_not_overwritten(tmp_path):
    database = tmp_path / "absent.sqlite3"
    assert saved_searches.list_saved(database).searches == []
    assert not database.exists() and not book_path(database).exists()
    book_path(database).write_text('{"schema_version":99}', encoding="utf-8")
    before = digest(book_path(database))
    with pytest.raises(ValueError):
        saved_searches.save(database, SavedSearch(name="new"))
    assert digest(book_path(database)) == before
    assert not database.exists()


def test_atomic_failure_and_writer_lock_preserve_previous_book(db, monkeypatch):
    before = digest(book_path(db))
    with collection_lock(book_path(db)):
        with pytest.raises(ValueError, match="Otra operación"):
            saved_searches.save(db, SavedSearch(name="new"))

    def fail(*args):
        raise OSError("simulated disk error")

    monkeypatch.setattr(saved_searches.os, "replace", fail)
    with pytest.raises(OSError):
        saved_searches.save(db, SavedSearch(name="new"))
    assert digest(book_path(db)) == before


def test_snapshot_stable_despite_live_change_and_no_private_data(db, monkeypatch):
    original = queries.search
    changed = False

    def change_live_after_first_read(*args, **kwargs):
        nonlocal changed
        result = original(*args, **kwargs)
        if not changed:
            changed = True
            with closing(Repository(db)) as repo, repo.connection:
                repo.connection.execute(
                    "UPDATE jobs SET payload=replace(payload,'Software','Other')"
                )
        return result

    monkeypatch.setattr(queries, "search", change_live_after_first_read)
    snapshot = evaluation.capture(db, "senior-uy", k=2)
    assert snapshot.sample.candidate_total == 4
    assert original(db, queries.Filters(query="Software"))["total"] == 0
    assert len(snapshot.sample.jobs) == 3
    assert "PRIVATE_NOT_FOR_EVALUATION" not in snapshot.model_dump_json()
    assert "personal" not in snapshot.model_dump_json()
    assert "remotive:0" in [item.job_key for item in snapshot.sample.rank_order]


def test_evaluation_unknowns_denominators_source_counts_and_mismatches(db, tmp_path):
    before = digest(db)
    snapshot = evaluation.capture(db, "senior-uy", k=2)
    labels = evaluation.label_template(snapshot)
    report = evaluation.evaluate(snapshot, labels)
    assert report["precision_delta"] is None
    assert report["rank"]["precision_lower"] == 0
    assert report["rank"]["precision_upper"] == 1
    for label in labels.labels:
        label.verdict = "useful" if label.job_key != "greenhouse%3Agitlab:0" else "not_useful"
    report = evaluation.evaluate(snapshot, labels)
    assert report["list"]["precision"] == 0.5
    assert report["rank"]["precision"] == 1
    assert report["precision_delta"] == 0.5
    assert report["useful_only_in_rank"] == ["remotive:0"]
    assert report["sources"]["remotive"]["collection"] == 2
    labels.labels[0].verdict = "unknown"
    assert evaluation.evaluate(snapshot, labels)["list"]["precision"] is None
    labels.snapshot_id = "wrong"
    with pytest.raises(ValueError, match="otra muestra"):
        evaluation.evaluate(snapshot, labels)
    labels.snapshot_id = snapshot.snapshot_id
    labels.labels.append(labels.labels[0])
    with pytest.raises(ValueError, match="exactamente"):
        evaluation.evaluate(snapshot, labels)
    path = tmp_path / "sample.json"
    export_file(snapshot.model_dump(), path, format="json", database=db)
    assert evaluation.load_snapshot(path).snapshot_id == snapshot.snapshot_id
    data = json.loads(path.read_text())
    data["sample"]["jobs"][0]["title"] = "Edited"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="muestra cambió"):
        evaluation.load_snapshot(path)
    assert digest(db) == before


def test_empty_and_small_samples_are_not_precision_at_ten(db):
    profile = saved_searches.get_saved(db, "senior-uy")
    profile.query = "does-not-exist"
    saved_searches.save(db, profile, replace=True)
    snapshot = evaluation.capture(db, profile.name)
    report = evaluation.evaluate(snapshot, evaluation.label_template(snapshot))
    assert report["rank"]["precision"] is None and report["rank"]["n"] == 0
    profile.query = "Junior"
    saved_searches.save(db, profile, replace=True)
    snapshot = evaluation.capture(db, profile.name)
    labels = evaluation.label_template(snapshot)
    labels.labels[0].verdict = "useful"
    report = evaluation.evaluate(snapshot, labels)
    assert report["k"] == 10 and report["rank"]["n"] == 1
    assert report["rank"]["precision"] == 1


def test_title_filter_shared_by_saved_cli_and_agent(db):
    from nicrawl.agent_tools import AgentTools

    profile = saved_searches.get_saved(db, "senior-uy")
    profile.title_query = "sEnIoR"
    profile.include_dismissed = True
    saved_searches.save(db, profile, replace=True)
    assert saved_searches.run_saved(db, profile.name)["total"] == 2
    cli = CliRunner().invoke(
        app, ["--db", str(db), "list", "--query", "Software", "--title-query", "sEnIoR"]
    )
    assert cli.exit_code == 0 and json.loads(cli.output)["total"] == 2
    response = AgentTools(db).call("search_jobs", {"query": "Software", "title_query": "sEnIoR"})
    assert response.total == 2
    assert evaluation.capture(db, profile.name).sample.candidate_total == 2


def test_cli_end_to_end_and_outputs_do_not_overwrite(db, tmp_path):
    runner = CliRunner()

    def invoke(*args):
        return runner.invoke(app, ["--db", str(db), "saved", *args])

    assert invoke("save", "other", "--query", "Software").exit_code == 0
    assert invoke("save", "other").exit_code == 1
    assert json.loads(invoke("run", "other").output)["total"] == 4
    snapshot, labels = tmp_path / "sample.json", tmp_path / "labels.json"
    assert invoke("snapshot", "senior-uy", "--output", str(snapshot)).exit_code == 0
    assert invoke("snapshot", "senior-uy", "--output", str(snapshot)).exit_code == 1
    assert (
        invoke("label-template", "--snapshot", str(snapshot), "--output", str(labels)).exit_code
        == 0
    )
    result = invoke("evaluate", "--snapshot", str(snapshot), "--labels", str(labels))
    assert result.exit_code == 0 and json.loads(result.output)["precision_delta"] is None
    assert invoke("delete", "other").exit_code == 0
