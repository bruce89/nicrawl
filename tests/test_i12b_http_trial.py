import hashlib
import json
import sqlite3
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing

import httpx
import pytest
from test_i12_simulation import draft as draft_fixture
from typer.testing import CliRunner

from nicrawl import applications as a
from nicrawl import http_trial as trial
from nicrawl.cli import app
from nicrawl.server import create_server
from nicrawl.test_receiver import canonical, create_receiver
from nicrawl.trial_store import receiver_path, receiver_token, sender_path

draft = draft_fixture


@pytest.fixture
def receiver(draft):
    db, material = draft
    server = create_receiver(db, 0, fault_delay=0.3)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield db, material, server.server_port
    finally:
        server.shutdown()
        server.server_close()
        thread.join(3)


def count_receipts(db):
    with closing(sqlite3.connect(receiver_path(db))) as con:
        return con.execute("SELECT count(*) FROM receipts").fetchone()[0]


@pytest.mark.parametrize("scenario,state", [("accepted", "accepted"), ("rejected", "rejected")])
def test_http_delivery_and_duplicate_result(receiver, scenario, state):
    db, material, port = receiver
    original = a.tracker_path(db).read_bytes()
    p = trial.prepare(db, material["id"], 1, port)
    assert trial.prepare(db, material["id"], 1, port)["id"] == p["id"]
    result = trial.send(db, p["id"], p["review_sha256"], scenario)
    assert result["state"] == state
    assert trial.send(db, p["id"], p["review_sha256"])["receipt_id"] == result["receipt_id"]
    assert count_receipts(db) == 1
    assert a.tracker_path(db).read_bytes() == original
    assert not db.exists()


@pytest.mark.parametrize("scenario,count", [("timeout-before", 0), ("timeout-after", 1)])
def test_real_read_timeout_and_reconciliation(receiver, scenario, count):
    db, material, port = receiver
    p = trial.prepare(db, material["id"], 1, port)
    result = trial.send(db, p["id"], p["review_sha256"], scenario, timeout=0.05)
    assert result["state"] == "uncertain"
    assert count_receipts(db) == count
    with pytest.raises(a.Conflict):
        trial.send(db, p["id"], p["review_sha256"])
    with pytest.raises(a.Conflict):
        trial.retry(db, p["id"], p["review_sha256"])
    result = trial.reconcile(db, p["id"])
    assert result["state"] == ("accepted" if count else "uncertain")
    if not count:
        result = trial.retry(db, p["id"], p["review_sha256"])
    assert result["state"] == "accepted"
    assert count_receipts(db) == 1


def test_interrupted_sender_recovers_through_reconciliation(receiver):
    db, material, port = receiver
    p = trial.prepare(db, material["id"], 1, port)
    trial.send(db, p["id"], p["review_sha256"], "timeout-before", timeout=0.05)
    # Simular interrupción del emisor después de persistir sending y antes de la respuesta.
    with closing(sqlite3.connect(sender_path(db))) as con:
        con.execute("UPDATE trials SET state='sending'")
        con.commit()
    assert trial.reconcile(db, p["id"])["state"] == "uncertain"
    assert trial.retry(db, p["id"], p["review_sha256"])["state"] == "accepted"


def test_confirmation_and_destination_cannot_be_changed(receiver):
    db, material, port = receiver
    p = trial.prepare(db, material["id"], 1, port)
    with pytest.raises(a.Conflict):
        trial.send(db, p["id"], "0" * 64)
    with pytest.raises(ValueError):
        trial.prepare(db, material["id"], 1, True)
    assert count_receipts(db) == 0
    assert trial.show(db, p["id"])["state"] == "prepared"


def test_receiver_rejects_unauthorized_and_conflicting_content(receiver):
    db, material, port = receiver
    p = trial.prepare(db, material["id"], 1, port)
    token = receiver_token(db)
    body = {
        "id": p["id"],
        "receiver_id": p["receiver_id"],
        "digest": p["review_sha256"],
        "payload": p["payload"],
        "scenario": "accepted",
    }
    with httpx.Client(base_url=f"http://127.0.0.1:{port}", trust_env=False) as client:
        assert client.post("/v1/submissions", json=body).status_code == 401
        headers = {"Authorization": f"Bearer {token}"}
        assert (
            client.post(
                "/v1/submissions", json=body, headers={**headers, "Origin": "http://127.0.0.1:8765"}
            ).status_code
            == 403
        )
        assert client.post("/v1/submissions", json=body, headers=headers).status_code == 200
        body["payload"] = {"different": "content"}
        body["digest"] = hashlib.sha256(canonical(body["payload"]).encode()).hexdigest()
        assert client.post("/v1/submissions", json=body, headers=headers).status_code == 409
    assert count_receipts(db) == 1


def test_concurrent_senders_do_not_duplicate(receiver):
    db, material, port = receiver
    p = trial.prepare(db, material["id"], 1, port)

    def send(_):
        try:
            return trial.send(db, p["id"], p["review_sha256"])["state"]
        except a.Conflict:
            return "busy"

    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(send, range(8)))
    assert "accepted" in results
    assert count_receipts(db) == 1


def test_invalid_receipt_keeps_uncertainty(receiver, monkeypatch):
    db, material, port = receiver
    p = trial.prepare(db, material["id"], 1, port)
    monkeypatch.setattr(
        trial,
        "_request",
        lambda *args, **kwargs: (
            200,
            {
                "protocol": "nicrawl-test-receiver-v1",
                "receiver_id": p["receiver_id"],
                "id": p["id"],
                "digest": "0" * 64,
                "receipt_id": p["id"],
                "result": "accepted",
            },
        ),
    )
    assert trial.send(db, p["id"], p["review_sha256"])["state"] == "uncertain"
    assert trial.reconcile(db, p["id"])["state"] == "uncertain"


def test_receiver_identity_change_blocks_delivery(receiver):
    db, material, port = receiver
    p = trial.prepare(db, material["id"], 1, port)
    # El proceso congela su identidad al iniciar. Alteramos solo el snapshot emisor
    # para representar un puerto ocupado por un receptor distinto al confirmado.
    with closing(sqlite3.connect(sender_path(db))) as con:
        con.execute("UPDATE trials SET receiver_id=?", ("0" * 32,))
        con.commit()
    assert trial.send(db, p["id"], p["review_sha256"])["state"] == "uncertain"
    assert count_receipts(db) == 0


def test_cli_and_ui_api_operate_same_trial(receiver):
    db, material, port = receiver
    result = CliRunner().invoke(
        app,
        [
            "--db",
            str(db),
            "http-trial",
            "prepare",
            material["id"],
            "--version",
            "1",
            "--port",
            str(port),
        ],
    )
    assert result.exit_code == 0, result.output
    p = json.loads(result.output)
    server = create_server(db, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with httpx.Client(
            base_url=f"http://127.0.0.1:{server.server_port}", trust_env=False
        ) as client:
            route = f"/api/http-trials/{p['id']}"
            assert client.get(route).json()["review_sha256"] == p["review_sha256"]
            sent = client.post(
                route + "/send", json={"review_sha256": p["review_sha256"], "scenario": "accepted"}
            )
            assert sent.json()["state"] == "accepted"
            assert client.post(route + "/retry", json={"review_sha256": "bad"}).status_code == 409
            assert (
                client.post(
                    "/api/http-trials",
                    json={
                        "draft_id": material["id"],
                        "version": 1,
                        "destination": "https://example.org",
                    },
                ).status_code
                == 400
            )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(3)


def test_receiver_separate_process_restart_preserves_receipts(draft, tmp_path):
    db, material = draft
    ready = tmp_path / "ready.txt"
    script = """
import sys, threading
from pathlib import Path
from nicrawl.test_receiver import create_receiver
s=create_receiver(Path(sys.argv[1]),int(sys.argv[3]))
t=threading.Thread(target=s.serve_forever,daemon=True);t.start()
Path(sys.argv[2]).write_text(str(s.server_port))
sys.stdin.readline()
s.shutdown();s.server_close();t.join(3)
"""
    port = 0
    p = None
    receipt = None
    for iteration in range(2):
        ready.unlink(missing_ok=True)
        process = subprocess.Popen(
            [sys.executable, "-c", script, str(db), str(ready), str(port)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            until = time.monotonic() + 8
            while not ready.exists() and process.poll() is None and time.monotonic() < until:
                time.sleep(0.05)
            assert ready.exists(), "El receptor hijo no arrancó"
            port = int(ready.read_text())
            if p is None:
                p = trial.prepare(db, material["id"], 1, port)
                receipt = trial.send(db, p["id"], p["review_sha256"])["receipt_id"]
            else:
                with closing(sqlite3.connect(sender_path(db))) as con:
                    con.execute("UPDATE trials SET state='uncertain',receipt_id=NULL")
                    con.commit()
                assert trial.reconcile(db, p["id"])["receipt_id"] == receipt
                assert count_receipts(db) == 1
        finally:
            try:
                process.communicate(b"\n", timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
        if iteration == 0:
            with closing(sqlite3.connect(sender_path(db))) as con:
                con.execute("UPDATE trials SET state='uncertain',receipt_id=NULL")
                con.commit()
            offline = trial.reconcile(db, p["id"])
            assert offline["state"] == "uncertain"
            assert offline["history"][-1]["action"] == "reconcile:unknown"
