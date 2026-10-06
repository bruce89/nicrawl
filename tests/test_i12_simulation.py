import json
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import httpx
import pytest
from typer.testing import CliRunner

from nicrawl import applications as a
from nicrawl import simulation as s
from nicrawl.cli import app
from nicrawl.server import create_server


@pytest.fixture
def draft(tmp_path):
    db = tmp_path / "jobs.sqlite3"
    application = a.create(
        db, a.Create(url="https://example.org/job/1", title="Engineer", company="Synthetic")
    )["application"]
    profile = a.save_profile(
        db,
        a.ProfileInput(
            label="Synthetic",
            cv_text="Python experience.",
            claims=[a.ClaimInput(statement="Python experience", evidence="Python experience.")],
        ),
    )
    material = a.create_draft(
        db, application["id"], a.DraftInput(profile_version=profile["version"], claim_ids=["E01"])
    )
    return db, material


def receipt_count(db):
    with closing(sqlite3.connect(s.store_path(db))) as con:
        return con.execute("SELECT count(*) FROM receipts").fetchone()[0]


@pytest.mark.parametrize(
    "scenario,result,count",
    [
        ("accepted", "accepted", 1),
        ("rejected", "rejected", 1),
        ("timeout-before", "prepared", 0),
        ("timeout-after", "accepted", 1),
    ],
)
def test_delivery_reconciliation_and_no_real_state_changes(draft, scenario, result, count):
    db, material = draft
    personal_before = a.tracker_path(db).read_bytes()
    prepared = s.prepare(db, material["id"], 1)
    sent = s.send(db, prepared["id"], prepared["review_sha256"], scenario)
    if scenario.startswith("timeout-"):
        assert sent["state"] == "uncertain" and sent["receipt_id"] is None
        with pytest.raises(a.Conflict):
            s.send(db, prepared["id"], prepared["review_sha256"])
    reconciled = s.reconcile(db, prepared["id"])
    assert reconciled["state"] == result
    assert receipt_count(db) == count
    assert a.tracker_path(db).read_bytes() == personal_before
    assert not db.exists()
    if result == "prepared":
        assert s.send(db, prepared["id"], prepared["review_sha256"])["state"] == "accepted"
        assert receipt_count(db) == 1


def test_concurrent_prepare_and_send_are_idempotent(draft):
    db, material = draft
    with ThreadPoolExecutor(4) as pool:
        prepared = list(pool.map(lambda _: s.prepare(db, material["id"], 1), range(8)))
    assert len({r["id"] for r in prepared}) == 1
    p = prepared[0]
    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(lambda _: s.send(db, p["id"], p["review_sha256"]), range(8)))
    assert len({r["receipt_id"] for r in results}) == 1
    assert receipt_count(db) == 1
    assert len(s.show(db, p["id"])["history"]) == 2


def test_snapshot_survives_new_draft_revision(draft):
    db, material = draft
    p = s.prepare(db, material["id"], 1)
    a.revise_draft(
        db, material["id"], 1, a.DraftInput(profile_version=1, opening="A different introduction")
    )
    assert s.show(db, p["id"])["payload"]["preview"] == material["preview"]
    assert s.prepare(db, material["id"], 1)["id"] == p["id"]
    assert s.prepare(db, material["id"], 2)["id"] != p["id"]
    with pytest.raises(a.Conflict):
        s.send(db, p["id"], "wrong-hash")
    assert s.show(db, p["id"])["state"] == "prepared"


def test_pending_questions_and_invalid_version_have_no_side_effects(draft):
    db, material = draft
    a.revise_draft(
        db,
        material["id"],
        1,
        a.DraftInput(profile_version=1, questions=["Can I work from Uruguay?"]),
    )
    with pytest.raises(ValueError):
        s.prepare(db, material["id"], 2)
    with pytest.raises(ValueError):
        s.prepare(db, material["id"], True)
    assert not s.store_path(db).exists()


def test_receiver_failure_rolls_back_entire_simulated_exchange(draft):
    db, material = draft
    p = s.prepare(db, material["id"], 1)
    with closing(sqlite3.connect(s.store_path(db))) as con:
        con.execute(
            "CREATE TRIGGER fail_event BEFORE INSERT ON events "
            "BEGIN SELECT RAISE(ABORT,'disk error'); END"
        )
        con.commit()
    with pytest.raises(sqlite3.Error):
        s.send(db, p["id"], p["review_sha256"])
    assert receipt_count(db) == 0
    assert s.show(db, p["id"])["state"] == "prepared"


def test_cli_and_api_share_durable_state(draft):
    db, material = draft
    runner = CliRunner()
    result = runner.invoke(
        app, ["--db", str(db), "simulation", "prepare", material["id"], "--version", "1"]
    )
    assert result.exit_code == 0, result.output
    p = json.loads(result.output)
    server = create_server(db, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with httpx.Client(
            base_url=f"http://127.0.0.1:{server.server_port}", trust_env=False
        ) as client:
            route = f"/api/simulations/{p['id']}"
            assert client.get(route).json()["review_sha256"] == p["review_sha256"]
            assert (
                client.post(
                    route + "/send", json={"review_sha256": "bad", "scenario": "accepted"}
                ).status_code
                == 409
            )
            body = {"review_sha256": p["review_sha256"], "scenario": "timeout-after"}
            assert (
                client.post(
                    route + "/send", json=body, headers={"Origin": "https://example.org"}
                ).status_code
                == 403
            )
            assert client.post(route + "/send", json=body).json()["state"] == "uncertain"
            assert client.post(route + "/send", json=body).status_code == 409
            assert client.post(route + "/reconcile", json={}).json()["state"] == "accepted"
            assert (
                client.post(
                    "/api/simulations", json={"draft_id": material["id"], "version": True}
                ).status_code
                == 400
            )
        assert s.show(db, p["id"])["state"] == "accepted"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(3)


def test_foreign_database_is_not_modified(draft):
    db, material = draft
    with closing(sqlite3.connect(s.store_path(db))) as con:
        con.execute("CREATE TABLE unrelated(id INTEGER)")
        con.commit()
    before = s.store_path(db).read_bytes()
    with pytest.raises(ValueError):
        s.prepare(db, material["id"], 1)
    assert s.store_path(db).read_bytes() == before


def test_legacy_tracker_lists_drafts_without_migrating(tmp_path):
    db = tmp_path / "legacy.sqlite3"
    with closing(sqlite3.connect(a.tracker_path(db))) as con:
        for statement in a.SCHEMA:
            con.execute(statement)
        con.execute(f"PRAGMA application_id={a.APP_ID}")
        con.execute("PRAGMA user_version=1")
        con.execute(
            "INSERT INTO applications VALUES('id',NULL,'Title','Company',"
            "'https://example.org','draft',1,'now','now')"
        )
        con.commit()
    before = a.tracker_path(db).read_bytes()
    assert a.list_drafts(db, "id") == {"drafts": []}
    assert a.tracker_path(db).read_bytes() == before
