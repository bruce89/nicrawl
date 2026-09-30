import csv
import json
from contextlib import closing
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from nicrawl import exporting, queries
from nicrawl.cli import app
from nicrawl.domain import JobDraft, Rejection
from nicrawl.sources.remotive import SourceBatch
from nicrawl.storage import Repository, StorageError

NOW = datetime(2026, 9, 26, tzinfo=UTC)


def draft(identifier="1", **fields):
    return replace(
        JobDraft(
            "remotive",
            identifier,
            "Straße Python",
            'Ñandú, "Co"',
            f"https://remotive.com/jobs/{identifier}",
            "SQL\nCafé",
            "Worldwide",
            None,
        ),
        **fields,
    )


def publish(repo, jobs, now=NOW, partial=False):
    run = repo.start_run(now)
    rejects = (Rejection(3, None, "title", "missing"),) if partial else ()
    repo.publish(
        run,
        SourceBatch(len(jobs) + len(rejects), tuple(jobs), rejects, 0),
        now,
        {"valid": len(jobs)},
    )
    return run


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "jobs.sqlite3"
    with closing(Repository(path)) as repo:
        publish(repo, [draft("2"), draft(), draft("3", title="Other", company="Other")])
    return path


def test_search_casefold_and_literal_substrings_and_order(database):
    result = queries.search(database, queries.Filters("STRASSE", "ÑANDÚ", "remotive", "world"))
    assert [job["job_key"] for job in result["jobs"]] == ["remotive:1", "remotive:2"]
    assert queries.search(database, queries.Filters("cafe"))["total"] == 0
    assert queries.search(database, queries.Filters("CAFÉ"))["total"] == 3
    assert queries.search(database, queries.Filters("%"))["total"] == 0
    assert queries.search(database, queries.Filters(company="absent"))["total"] == 0
    assert queries.search(database, queries.Filters(source="other"))["total"] == 0
    assert queries.search(database, limit=1)["total"] == 3


def test_detail_freshness_and_missing(database):
    assert queries.show(database, "remotive:1")["job"]["salary_raw"] is None
    assert not queries.search(database, now=NOW + timedelta(days=7))["jobs"][0]["stale"]
    assert queries.search(database, now=NOW + timedelta(days=7, seconds=1))["jobs"][0]["stale"]
    with pytest.raises(StorageError, match="no encontrada"):
        queries.show(database, "remotive:999")


def test_changes_latest_partial_ignores_failure_and_preserves_history(database):
    with closing(Repository(database)) as repo:
        original = queries.changes(database)["published_run"]["run_id"]
        updated = publish(
            repo, [draft(title="Changed"), draft("2")], NOW + timedelta(hours=1), True
        )
        failed = repo.start_run(NOW + timedelta(hours=2))
        repo.finish(failed, NOW, "failed", "test", {})
    result = queries.changes(database)
    assert result["published_run"]["run_id"] == updated
    assert result["published_run"]["status"] == "partial"
    assert result["source_status"]["run"]["status"] == "failed"
    assert result["changes"][0]["fields"] == ["title"]
    assert result["changes"][0]["before"]["title"] == "Straße Python"
    assert queries.changes(database, run=original)["total"] == 3
    assert (
        queries.changes(database, run=original)["changes"][0]["after"]["title"] == "Straße Python"
    )
    with pytest.raises(StorageError):
        queries.changes(database, run=failed)


def test_unchanged_published_run_has_zero_changes(database):
    with closing(Repository(database)) as repo:
        publish(repo, [draft()], NOW + timedelta(hours=1))
    assert queries.changes(database)["total"] == 0
    assert queries.search(database)["total"] == 3  # Ausencia no implica cierre.


@pytest.mark.parametrize(
    "cell",
    ["=1+1", "+1", "-1", "@SUM(A1)", "  =1", "\ttext", "\rtext", " \u200b=1", "\x1b[31mtext"],
)
def test_csv_formula_prefixes(cell):
    assert exporting.csv_cell(cell) == "'" + cell


def test_roundtrip_csv_json_and_same_selection(database, tmp_path):
    report = queries.search(database, queries.Filters(query="STRASSE"))
    report["jobs"][0]["description_text"] = '=SUM(1,2)\n"Café"'
    for format in ("json", "csv"):
        target = tmp_path / f"result.{format}"
        exporting.export_file(report, target, format=format, database=database)
        if format == "json":
            exported = json.loads(target.read_text("utf-8"))
            assert exported.pop("exported_at")
            assert exported == report
        else:
            with target.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            assert len(rows) == 2
            assert rows[0]["company"] == 'Ñandú, "Co"'
            assert rows[0]["description_text"] == '\'=SUM(1,2)\n"Café"'
            assert rows[0]["source_url"].startswith("https://remotive.com/")
            assert rows[0]["last_seen_at"] == NOW.isoformat()


def test_export_existing_and_failed_write_preserve_destination(database, tmp_path, monkeypatch):
    target = tmp_path / "keep.json"
    target.write_bytes(b"original")
    report = queries.search(database)
    with pytest.raises(FileExistsError):
        exporting.export_file(report, target, format="json", database=database)

    def fail(stream, report, format):
        stream.write("incomplete")
        raise OSError("disk full")

    monkeypatch.setattr(exporting, "_write", fail)
    with pytest.raises(OSError):
        exporting.export_file(report, target, format="json", database=database, overwrite=True)
    assert target.read_bytes() == b"original"
    assert not list(tmp_path.glob(".nicrawl-*.tmp"))


def test_publish_race_and_replace_failure(database, tmp_path, monkeypatch):
    target = tmp_path / "race.json"
    original = exporting._write

    def race(stream, report, format):
        original(stream, report, format)
        target.write_bytes(b"competitor")

    monkeypatch.setattr(exporting, "_write", race)
    with pytest.raises(FileExistsError):
        exporting.export_file(queries.search(database), target, format="json", database=database)
    assert target.read_bytes() == b"competitor"
    monkeypatch.setattr(exporting, "_write", original)

    def fail(*args):
        raise OSError("replace failed")

    monkeypatch.setattr(exporting.os, "replace", fail)
    with pytest.raises(OSError):
        exporting.export_file(
            queries.search(database), target, format="json", database=database, overwrite=True
        )
    assert target.read_bytes() == b"competitor"
    assert not list(tmp_path.glob(".nicrawl-*.tmp"))


def test_export_cannot_replace_database_or_hardlink(database, tmp_path):
    alias = tmp_path / "alias"
    alias.hardlink_to(database)
    for target in (database, alias, Path(str(database) + "-wal")):
        with pytest.raises(ValueError, match="base"):
            exporting.export_file(
                queries.search(database), target, format="json", database=database, overwrite=True
            )
    assert queries.search(database)["total"] == 3


def test_cli_offline_and_safe_json(database, tmp_path):
    with closing(Repository(database)) as repo:
        publish(repo, [draft(title="\x1b[31mDanger\u202e")], NOW + timedelta(hours=1))
    runner = CliRunner()
    before = database.read_bytes()
    for args in (["list"], ["show", "remotive:1"], ["changes"]):
        result = runner.invoke(app, ["--db", str(database), *args])
        assert result.exit_code == 0, result.output
        assert "\x1b" not in result.output and "\u202e" not in result.output
        json.loads(result.output)
    dest = tmp_path / "out.json"
    args = ["--db", str(database), "export", "--output", str(dest), "--query", "danger"]
    assert runner.invoke(app, args).exit_code == 0
    assert len(json.loads(dest.read_text("utf-8"))["jobs"]) == 1
    assert runner.invoke(app, args).exit_code == 1
    assert runner.invoke(app, args + ["--overwrite"]).exit_code == 0
    assert database.read_bytes() == before


def test_missing_database_does_not_create_and_invalid_limit(tmp_path):
    db = tmp_path / "missing.db"
    runner = CliRunner()
    for args in (
        ["list"],
        ["show", "x"],
        ["changes"],
        ["export", "--output", str(tmp_path / "out.json")],
    ):
        assert runner.invoke(app, ["--db", str(db), *args]).exit_code == 1
    assert not db.exists()
    assert runner.invoke(app, ["list", "--limit", "201"]).exit_code == 2


def test_empty_export_and_all_results(database, tmp_path):
    report = queries.search(database, queries.Filters("not present"))
    dest = tmp_path / "empty.csv"
    exporting.export_file(report, dest, format="csv", database=database)
    assert len(dest.read_text("utf-8").splitlines()) == 1
    with closing(Repository(database)) as repo:
        publish(repo, [draft(str(i)) for i in range(1, 24)], NOW + timedelta(hours=1))
    runner = CliRunner()
    dest = tmp_path / "all.json"
    result = runner.invoke(app, ["--db", str(database), "export", "--output", str(dest)])
    assert result.exit_code == 0, result.output
    assert len(json.loads(dest.read_text("utf-8"))["jobs"]) == 23
    assert result.stdout == ""
    assert (
        runner.invoke(
            app,
            ["--db", str(database), "export", "--output", str(dest), "--limit", "1", "--overwrite"],
        ).exit_code
        == 0
    )
    assert len(json.loads(dest.read_text("utf-8"))["jobs"]) == 1
