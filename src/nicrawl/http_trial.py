"""Emisor del ensayo HTTP: snapshot confirmado, incertidumbre y reintento idempotente."""

import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from nicrawl import applications
from nicrawl.simulation import SCENARIOS
from nicrawl.test_receiver import MAX_BODY, MAX_RESPONSE, PORT, Info, Receipt, canonical
from nicrawl.trial_store import SENDER_ID, connect, event, receiver_token, report, row, sender_path


def _request(
    database: Path,
    port: int,
    method: str,
    route: str,
    body: dict[str, Any] | None = None,
    *,
    timeout: float = 2,
) -> tuple[int, Any]:
    # URL construida exclusivamente con loopback literal; no DNS, proxies ni redirects.
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Puerto local inválido.")
    token = receiver_token(database)
    with httpx.Client(trust_env=False, follow_redirects=False, timeout=timeout) as client:
        with client.stream(
            method,
            f"http://127.0.0.1:{port}{route}",
            json=body,
            headers={"Authorization": f"Bearer {token}"},
        ) as response:
            chunks = bytearray()
            for chunk in response.iter_bytes(chunk_size=MAX_RESPONSE + 1):
                chunks.extend(chunk)
                if len(chunks) > MAX_RESPONSE:
                    raise ValueError("Respuesta de receptor demasiado grande.")
            return response.status_code, json.loads(chunks)


def prepare(database: Path, draft_id: str, version: int, port: int = PORT) -> dict[str, Any]:
    if type(version) is not int or version < 1:
        raise ValueError("La versión debe ser un entero positivo.")
    draft = applications.show_draft(database, draft_id, version)
    if draft["questions"]:
        raise ValueError("Resolvé las preguntas pendientes antes de preparar el ensayo HTTP.")
    try:
        code, data = _request(database, port, "GET", "/v1/info")
        if code != 200:
            raise ValueError("Receptor no autorizado o incompatible.")
        info = Info.model_validate(data)
    except httpx.HTTPError as error:
        raise ValueError(
            "No se pudo conectar al receptor. Iniciá nicrawl test-receiver."
        ) from error
    payload = {
        key: draft[key] for key in ("id", "application_id", "version", "profile_version", "preview")
    }
    payload.update(destination=f"http://127.0.0.1:{port}", receiver_id=info.receiver_id)
    raw = canonical(payload)
    if len(raw.encode("utf-8")) > MAX_BODY - 1024:
        raise ValueError("Borrador demasiado grande para este laboratorio.")
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    with connect(sender_path(database), SENDER_ID, write=True) as con:
        old = con.execute(
            "SELECT id,digest FROM trials WHERE draft_id=? AND draft_version=? "
            "AND port=? AND receiver_id=?",
            (draft_id, version, port, info.receiver_id),
        ).fetchone()
        if old:
            if old["digest"] != digest:
                raise applications.Conflict("Cambió el contenido de la revisión preparada.")
            return report(con, old["id"])
        identifier = str(uuid4())
        con.execute(
            "INSERT INTO trials(id,draft_id,draft_version,port,receiver_id,payload,digest,state) "
            "VALUES(?,?,?,?,?,?,?,'prepared')",
            (identifier, draft_id, version, port, info.receiver_id, raw, digest),
        )
        event(con, identifier, "prepared", "prepared")
        return report(con, identifier)


def show(database: Path, identifier: str) -> dict[str, Any]:
    if not sender_path(database).exists():
        raise applications.NotFound("Ensayo HTTP no encontrado.")
    with connect(sender_path(database), SENDER_ID) as con:
        return report(con, identifier)


def _finish(
    database: Path,
    identifier: str,
    state: str,
    action: str,
    receipt: Receipt | None = None,
    message: str = "",
) -> dict[str, Any]:
    with connect(sender_path(database), SENDER_ID, write=True) as con:
        current = row(con, identifier)
        if current["state"] in {"accepted", "rejected"}:
            return report(con, identifier)
        if receipt:
            con.execute(
                "UPDATE trials SET receipt_id=? WHERE id=?", (receipt.receipt_id, identifier)
            )
        event(con, identifier, action, state, message)
        return report(con, identifier)


def _receipt(data: Any, trial: dict[str, Any]) -> Receipt:
    receipt = Receipt.model_validate(data)
    if (
        receipt.id != trial["id"]
        or receipt.digest != trial["review_sha256"]
        or receipt.receiver_id != trial["receiver_id"]
    ):
        raise ValueError("El recibo no corresponde a este contenido y receptor.")
    return receipt


def send(
    database: Path,
    identifier: str,
    review_sha256: str,
    scenario: str = "accepted",
    *,
    retry: bool = False,
    timeout: float = 2,
) -> dict[str, Any]:
    if scenario not in SCENARIOS:
        raise ValueError("Escenario desconocido.")
    trial = show(database, identifier)
    # Validar el token antes de registrar un intento; su valor nunca se registra.
    receiver_token(database)
    with connect(sender_path(database), SENDER_ID, write=True) as con:
        current = row(con, identifier)
        if current["digest"] != review_sha256:
            raise applications.Conflict("La confirmación no coincide con el contenido preparado.")
        if current["state"] in {"accepted", "rejected"}:
            return report(con, identifier)
        expected = "uncertain" if retry else "prepared"
        if current["state"] != expected:
            raise applications.Conflict(
                "Consultá el recibo; reintentar un resultado incierto requiere retry."
            )
        if retry:
            last = con.execute(
                "SELECT action FROM events WHERE trial_id=? ORDER BY sequence DESC LIMIT 1",
                (identifier,),
            ).fetchone()
            if last is None or not last["action"].startswith("reconcile:"):
                raise applications.Conflict("Consultá el recibo antes del reintento explícito.")
            scenario = current["scenario"]
        con.execute("UPDATE trials SET scenario=? WHERE id=?", (scenario, identifier))
        event(con, identifier, "retry" if retry else "send", "sending")
    # Commit antes de HTTP: incluso si muere este proceso, hay un ID para reconciliar.
    envelope = {
        "id": identifier,
        "receiver_id": trial["receiver_id"],
        "digest": trial["review_sha256"],
        "payload": trial["payload"],
        "scenario": scenario,
    }
    port = int(trial["destination"].rsplit(":", 1)[1])
    try:
        code, data = _request(database, port, "POST", "/v1/submissions", envelope, timeout=timeout)
        if code != 200:
            raise ValueError("Respuesta HTTP no confirmada.")
        receipt = _receipt(data, trial)
    except httpx.HTTPError, ValueError, OSError:
        return _finish(
            database,
            identifier,
            "uncertain",
            "response:unknown",
            message="No se confirmó la respuesta. Consultá el recibo antes de reintentar.",
        )
    return _finish(database, identifier, receipt.result, "response:receipt", receipt)


def reconcile(database: Path, identifier: str, *, timeout: float = 2) -> dict[str, Any]:
    trial = show(database, identifier)
    if trial["state"] in {"accepted", "rejected", "prepared"}:
        return trial
    port = int(trial["destination"].rsplit(":", 1)[1])
    try:
        code, data = _request(database, port, "GET", f"/v1/receipts/{identifier}", timeout=timeout)
        if code == 404:
            info = Info.model_validate(data)
            if info.receiver_id != trial["receiver_id"]:
                raise ValueError("Cambió el receptor.")
            return _finish(
                database,
                identifier,
                "uncertain",
                "reconcile:absent",
                message="Sin recibo todavía. Podés reintentar explícitamente con la misma clave.",
            )
        if code != 200:
            raise ValueError("No se pudo consultar el recibo.")
        receipt = _receipt(data, trial)
    except httpx.HTTPError, ValueError, OSError:
        return _finish(
            database,
            identifier,
            "uncertain",
            "reconcile:unknown",
            message="Consulta sin resultado confirmado; el ensayo sigue incierto.",
        )
    return _finish(database, identifier, receipt.result, "reconcile:receipt", receipt)


def retry(database: Path, identifier: str, review_sha256: str) -> dict[str, Any]:
    return send(database, identifier, review_sha256, retry=True)
