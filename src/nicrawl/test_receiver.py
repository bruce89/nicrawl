"""Receptor HTTP de ensayo: loopback, token local y recibos idempotentes durables."""

import hashlib
import json
import secrets
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import uuid4

from pydantic import Field

from nicrawl.applications import Contract
from nicrawl.trial_store import RECEIVER_ID, connect, receiver_path, receiver_token

PROTOCOL = "nicrawl-test-receiver-v1"
MAX_BODY = 2_000_000
MAX_RESPONSE = 8192
PORT = 8766
HOST = "127.0.0.1"
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Identifier = Annotated[str, Field(pattern=r"^[a-f0-9-]{36}$")]


def canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class Envelope(Contract):
    id: Identifier
    receiver_id: Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]
    digest: Digest
    payload: dict[str, Any]
    scenario: Literal["accepted", "rejected", "timeout-before", "timeout-after"]


class Info(Contract):
    protocol: Literal["nicrawl-test-receiver-v1"]
    receiver_id: Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]


class Receipt(Info):
    id: Identifier
    digest: Digest
    result: Literal["accepted", "rejected"]
    receipt_id: Identifier


def create_receiver(
    database: Path, port: int = PORT, *, fault_delay: float = 3
) -> ThreadingHTTPServer:
    if not 0 <= port <= 65535 or fault_delay < 0:
        raise ValueError("Puerto o demora inválidos.")
    path = receiver_path(database)
    with connect(path, RECEIVER_ID, write=True) as con:
        identity = con.execute("SELECT id FROM identity").fetchone()[0]
    token = receiver_token(database, create=True)

    class Handler(BaseHTTPRequestHandler):
        def respond(self, status: int, body: dict[str, Any]) -> None:
            raw = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            try:
                self.wfile.write(raw)
            except BrokenPipeError, ConnectionResetError:
                pass

        def authorized(self) -> bool:
            expected = f"{HOST}:{server.server_port}"
            if self.headers.get("Host") != expected or self.headers.get("Origin") is not None:
                self.respond(403, {"error": "Origen no permitido."})
                return False
            if not secrets.compare_digest(
                self.headers.get("Authorization", "").encode("utf-8"),
                f"Bearer {token}".encode("ascii"),
            ):
                self.respond(401, {"error": "Token local requerido."})
                return False
            return True

        def do_GET(self) -> None:
            if not self.authorized():
                return
            if self.path == "/v1/info":
                self.respond(200, {"protocol": PROTOCOL, "receiver_id": identity})
                return
            if not self.path.startswith("/v1/receipts/"):
                self.respond(404, {"error": "Ruta desconocida."})
                return
            identifier = self.path[len("/v1/receipts/") :]
            try:
                with connect(path, RECEIVER_ID) as con:
                    item = con.execute(
                        "SELECT * FROM receipts WHERE id=?", (identifier,)
                    ).fetchone()
                if item is None:
                    self.respond(404, {"protocol": PROTOCOL, "receiver_id": identity})
                else:
                    self.respond(
                        200,
                        {
                            "protocol": PROTOCOL,
                            "receiver_id": identity,
                            "id": identifier,
                            "digest": item["digest"],
                            "result": item["result"],
                            "receipt_id": item["receipt_id"],
                        },
                    )
            except sqlite3.Error, OSError, ValueError:
                self.respond(500, {"error": "Error del almacén receptor."})

        def do_POST(self) -> None:
            self.connection.settimeout(5)
            try:
                length = int(self.headers.get("Content-Length", ""))
                if self.headers.get("Transfer-Encoding") or not 1 <= length <= MAX_BODY:
                    raise ValueError("Cuerpo fuera del límite permitido.")
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError("Cuerpo incompleto.")
                if not self.authorized():
                    return
                if self.path != "/v1/submissions":
                    self.respond(404, {"error": "Ruta desconocida."})
                    return
                if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    raise ValueError("Se requiere JSON.")
                envelope = Envelope.model_validate_json(raw)
                if envelope.receiver_id != identity:
                    self.respond(409, {"error": "Cambió la identidad del receptor."})
                    return
                payload = canonical(envelope.payload)
                if hashlib.sha256(payload.encode("utf-8")).hexdigest() != envelope.digest:
                    raise ValueError("Hash de contenido incorrecto.")
                with connect(path, RECEIVER_ID, write=True) as con:
                    old = con.execute(
                        "SELECT * FROM requests WHERE id=?", (envelope.id,)
                    ).fetchone()
                    if old and (
                        old["digest"] != envelope.digest or old["scenario"] != envelope.scenario
                    ):
                        self.respond(
                            409, {"error": "Identificador reutilizado con otro contenido."}
                        )
                        return
                    first = old is None
                    if first:
                        con.execute(
                            "INSERT INTO requests VALUES(?,?,?)",
                            (envelope.id, envelope.digest, envelope.scenario),
                        )
                    if not (first and envelope.scenario == "timeout-before"):
                        con.execute(
                            "INSERT OR IGNORE INTO receipts VALUES(?,?,?,?,?)",
                            (
                                envelope.id,
                                envelope.digest,
                                str(uuid4()),
                                "rejected" if envelope.scenario == "rejected" else "accepted",
                                payload,
                            ),
                        )
                    receipt = con.execute(
                        "SELECT * FROM receipts WHERE id=?", (envelope.id,)
                    ).fetchone()
                # El commit ocurre antes de demorar la respuesta: son fallos de red observables.
                if first and envelope.scenario.startswith("timeout-"):
                    time.sleep(fault_delay)
                if receipt is None:
                    self.respond(503, {"error": "Fallo de ensayo antes de recibir."})
                else:
                    self.respond(
                        200,
                        {
                            "protocol": PROTOCOL,
                            "receiver_id": identity,
                            "id": envelope.id,
                            "digest": receipt["digest"],
                            "receipt_id": receipt["receipt_id"],
                            "result": receipt["result"],
                        },
                    )
            except ValueError:
                self.respond(400, {"error": "Solicitud inválida."})
            except sqlite3.Error, OSError:
                self.respond(500, {"error": "Error local del receptor."})

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer((HOST, port), Handler)
    server.daemon_threads = True
    return server
