"""API HTTP local y archivos de UI; los casos de uso viven en queries/personal."""

import json
import sqlite3
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs, unquote, urlsplit

from nicrawl import applications, http_trial, queries, saved_searches, simulation
from nicrawl.personal import Preferences, mark, rank
from nicrawl.storage import StorageError

HOST = "127.0.0.1"
SOURCES = {"", "remotive", "greenhouse:gitlab"}
STATIC = {
    "/applications": ("applications.html", "text/html; charset=utf-8"),
    "/applications.js": ("applications.js", "text/javascript; charset=utf-8"),
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}


def _single(parameters: dict[str, list[str]], name: str, default: str = "") -> str:
    values = parameters.get(name)
    if values is None:
        return default
    if len(values) != 1:
        raise ValueError(f"Parámetro repetido: {name}.")
    value = values[0]
    if len(value) > 120:
        raise ValueError(f"Parámetro demasiado largo: {name}.")
    return value


def _filters(parameters: dict[str, list[str]]) -> queries.Filters:
    source = _single(parameters, "source")
    if source not in SOURCES:
        raise ValueError("Fuente desconocida.")
    return queries.Filters(
        _single(parameters, "query"),
        _single(parameters, "company"),
        source,
        _single(parameters, "location_text"),
        _single(parameters, "title_query"),
    )


def _limit(parameters: dict[str, list[str]]) -> int:
    raw = _single(parameters, "limit", "20")
    try:
        limit = int(raw)
    except ValueError as error:
        raise ValueError("limit debe ser un entero entre 1 y 200.") from error
    if not 1 <= limit <= 200:
        raise ValueError("limit debe estar entre 1 y 200.")
    return limit


def _terms(parameters: dict[str, list[str]], name: str) -> tuple[str, ...]:
    values = parameters.get(name, [])
    return tuple(value.strip() for value in values)


def _rank_preferences(parameters: dict[str, list[str]]) -> Preferences:
    fields = _single(parameters, "fields", "title,tags,description")
    mode = _single(parameters, "mode") or None
    return Preferences(
        want=_terms(parameters, "want"),
        avoid=_terms(parameters, "avoid"),
        mode=mode,
        fields=tuple(part.strip() for part in fields.split(",") if part.strip()),
    )


def _include_dismissed(parameters: dict[str, list[str]]) -> bool:
    raw = _single(parameters, "include_dismissed", "false")
    if raw not in {"true", "false"}:
        raise ValueError("include_dismissed debe ser true o false.")
    return raw == "true"


def create_server(database: Path, port: int = 8765) -> ThreadingHTTPServer:
    """Crear servidor exclusivamente sobre loopback; port=0 permite pruebas aisladas."""
    if not 0 <= port <= 65535:
        raise ValueError("El puerto debe estar entre 0 y 65535.")
    database = database.resolve()

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: HTTPStatus, content: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "connect-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'",
            )
            self.end_headers()
            self.wfile.write(content)

        def _json(self, status: HTTPStatus, data: dict[str, Any]) -> None:
            self._send(
                status,
                json.dumps(data, ensure_ascii=False).encode("utf-8"),
                "application/json; charset=utf-8",
            )

        def _host_allowed(self) -> bool:
            port = cast(ThreadingHTTPServer, self.server).server_port
            if self.headers.get("Host") != f"{HOST}:{port}":
                self._json(HTTPStatus.FORBIDDEN, {"error": "Host local no permitido."})
                return False
            return True

        def _origin_allowed(self) -> bool:
            origin = self.headers.get("Origin")
            port = cast(ThreadingHTTPServer, self.server).server_port
            if origin is not None and origin != f"http://{HOST}:{port}":
                self._json(HTTPStatus.FORBIDDEN, {"error": "Origin no permitido."})
                return False
            return True

        def _parameters(self, query: str, allowed: set[str]) -> dict[str, list[str]]:
            parameters = parse_qs(query, keep_blank_values=True, max_num_fields=40)
            unknown = set(parameters) - allowed
            if unknown:
                raise ValueError("Parámetros desconocidos: " + ", ".join(sorted(unknown)))
            return parameters

        def _error(self, error: Exception) -> None:
            if isinstance(error, applications.NotFound):
                status = HTTPStatus.NOT_FOUND
            elif isinstance(error, applications.Conflict):
                status = HTTPStatus.CONFLICT
            elif isinstance(error, StorageError):
                status = (
                    HTTPStatus.NOT_FOUND
                    if str(error).startswith(("Oferta no encontrada", "No hay base local"))
                    else HTTPStatus.CONFLICT
                )
            elif isinstance(error, (ValueError, UnicodeError)):
                status = HTTPStatus.BAD_REQUEST
            else:
                status = HTTPStatus.INTERNAL_SERVER_ERROR
            message = str(error) if status != HTTPStatus.INTERNAL_SERVER_ERROR else "Error local."
            self._json(status, {"error": message})

        def do_GET(self) -> None:
            if not self._host_allowed():
                return
            route = urlsplit(self.path)
            if route.path in STATIC and not route.query:
                name, content_type = STATIC[route.path]
                content = files("nicrawl.ui").joinpath(name).read_bytes()
                self._send(HTTPStatus.OK, content, content_type)
                return
            try:
                if route.path == "/api/health":
                    if route.query:
                        raise ValueError("health no acepta parámetros.")
                    self._json(HTTPStatus.OK, {"status": "ok", "database": str(database)})
                elif route.path == "/api/searches" and not route.query:
                    self._json(HTTPStatus.OK, saved_searches.list_saved(database).model_dump())
                elif route.path == "/api/applications":
                    params = self._parameters(route.query, {"state", "limit"})
                    self._json(
                        HTTPStatus.OK,
                        applications.list_applications(
                            database, state=_single(params, "state"), limit=_limit(params)
                        ),
                    )
                elif route.path.startswith("/api/http-trials/") and not route.query:
                    self._json(
                        HTTPStatus.OK,
                        http_trial.show(database, route.path[len("/api/http-trials/") :]),
                    )
                elif route.path.startswith("/api/simulations/") and not route.query:
                    self._json(
                        HTTPStatus.OK,
                        simulation.show(database, route.path[len("/api/simulations/") :]),
                    )
                elif route.path == "/api/profiles" and not route.query:
                    self._json(HTTPStatus.OK, applications.list_profiles(database))
                elif route.path.startswith("/api/profiles/") and not route.query:
                    raw_version = route.path[len("/api/profiles/") :]
                    if not raw_version.isdigit():
                        raise ValueError("Versión de perfil inválida.")
                    self._json(HTTPStatus.OK, applications.get_profile(database, int(raw_version)))
                elif route.path.startswith("/api/applications/") and route.path.endswith("/drafts"):
                    if route.query:
                        raise ValueError("La lista de borradores no acepta parámetros.")
                    application_id = route.path[len("/api/applications/") : -len("/drafts")].rstrip(
                        "/"
                    )
                    self._json(HTTPStatus.OK, applications.list_drafts(database, application_id))
                elif route.path.startswith("/api/drafts/"):
                    params = self._parameters(route.query, {"version"})
                    raw_version = _single(params, "version")
                    if raw_version and not raw_version.isdigit():
                        raise ValueError("Versión de borrador inválida.")
                    self._json(
                        HTTPStatus.OK,
                        applications.show_draft(
                            database,
                            route.path[len("/api/drafts/") :],
                            int(raw_version) if raw_version else None,
                        ),
                    )
                elif route.path.startswith("/api/applications/") and not route.query:
                    self._json(
                        HTTPStatus.OK,
                        applications.show(database, route.path[len("/api/applications/") :]),
                    )
                elif route.path.startswith("/api/searches/") and not route.query:
                    name = route.path[len("/api/searches/") :]
                    if name.endswith("/run"):
                        self._json(HTTPStatus.OK, saved_searches.run_saved(database, name[:-4]))
                    else:
                        self._json(
                            HTTPStatus.OK, saved_searches.get_saved(database, name).model_dump()
                        )
                elif route.path == "/api/jobs":
                    params = self._parameters(
                        route.query,
                        {"query", "title_query", "company", "source", "location_text", "limit"},
                    )
                    self._json(
                        HTTPStatus.OK,
                        queries.search(database, _filters(params), limit=_limit(params)),
                    )
                elif route.path == "/api/rank":
                    params = self._parameters(
                        route.query,
                        {
                            "query",
                            "title_query",
                            "company",
                            "source",
                            "location_text",
                            "limit",
                            "want",
                            "avoid",
                            "mode",
                            "fields",
                            "include_dismissed",
                        },
                    )
                    self._json(
                        HTTPStatus.OK,
                        rank(
                            database,
                            _rank_preferences(params),
                            filters=_filters(params),
                            limit=_limit(params),
                            include_dismissed=_include_dismissed(params),
                        ),
                    )
                elif route.path.startswith("/api/jobs/") and route.query == "":
                    key = unquote(route.path[len("/api/jobs/") :])
                    if not key or "/" in key or len(key) > 300:
                        raise ValueError("job_key inválido.")
                    self._json(HTTPStatus.OK, queries.show(database, key))
                else:
                    self._json(HTTPStatus.NOT_FOUND, {"error": "Ruta no encontrada."})
            except (StorageError, sqlite3.Error, OSError, ValueError, UnicodeError) as error:
                self._error(error)

        def do_PATCH(self) -> None:
            if urlsplit(self.path).path.startswith("/api/applications/"):
                self._application_write(create=False)
                return
            # Consumir el cuerpo acotado antes de rechazar cabeceras: cerrar con
            # bytes pendientes puede provocar un TCP reset en Windows.
            self.connection.settimeout(2)
            try:
                length = int(self.headers.get("Content-Length", ""))
                if self.headers.get("Transfer-Encoding") or not 1 <= length <= 4096:
                    raise ValueError("Cuerpo fuera de límite (1–4096 bytes).")
                raw_body = self.rfile.read(length)
                if len(raw_body) != length:
                    raise ValueError("Cuerpo incompleto.")
            except (OSError, ValueError) as error:
                self._error(error)
                return
            if not self._host_allowed() or not self._origin_allowed():
                return
            route = urlsplit(self.path)
            if (
                not route.path.startswith("/api/jobs/")
                or not route.path.endswith("/personal")
                or route.query
            ):
                self._json(HTTPStatus.NOT_FOUND, {"error": "Ruta no encontrada."})
                return
            key = unquote(route.path[len("/api/jobs/") : -len("/personal")])
            if not key or "/" in key or len(key) > 300:
                self._json(HTTPStatus.BAD_REQUEST, {"error": "job_key inválido."})
                return
            if (
                self.headers.get("Content-Type", "").split(";")[0].strip().lower()
                != "application/json"
            ):
                self._json(
                    HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "Se requiere application/json."}
                )
                return
            try:
                body = json.loads(raw_body)
                if not isinstance(body, dict) or set(body) - {"state", "note", "clear_note"}:
                    raise ValueError("Campos permitidos: state, note, clear_note.")
                state = body.get("state")
                note = body.get("note")
                clear_note = body.get("clear_note", False)
                if (
                    (state is not None and not isinstance(state, str))
                    or (note is not None and not isinstance(note, str))
                    or not isinstance(clear_note, bool)
                ):
                    raise ValueError("Tipos inválidos en estado personal.")
                self._json(
                    HTTPStatus.OK,
                    mark(database, key, state=state, note=note, clear_note=clear_note),
                )
            except (StorageError, sqlite3.Error, OSError, ValueError, UnicodeError) as error:
                self._error(error)

        def do_PUT(self) -> None:
            self.connection.settimeout(10)
            try:
                path = urlsplit(self.path).path
                length = int(self.headers.get("Content-Length", ""))
                limit = (
                    2500000
                    if path == "/api/profiles"
                    else 16384
                    if path.startswith("/api/drafts/")
                    else 8192
                )
                if self.headers.get("Transfer-Encoding") or not 1 <= length <= limit:
                    raise ValueError("Cuerpo fuera del límite permitido.")
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError("Cuerpo incompleto.")
                if not self._host_allowed() or not self._origin_allowed():
                    return
                if (
                    self.headers.get("Content-Type", "").split(";")[0].strip().lower()
                    != "application/json"
                ):
                    self._json(
                        HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                        {"error": "Se requiere application/json."},
                    )
                    return
                body = json.loads(raw)
                if path == "/api/profiles":
                    result = applications.save_profile(
                        database, applications.ProfileInput.model_validate(body)
                    )
                    self._json(HTTPStatus.CREATED, result)
                elif path.startswith("/api/drafts/"):
                    if not isinstance(body, dict) or set(body) != {"expected_version", "draft"}:
                        raise ValueError("Campos requeridos: expected_version, draft.")
                    expected = body["expected_version"]
                    if isinstance(expected, bool) or not isinstance(expected, int) or expected < 1:
                        raise ValueError("expected_version debe ser un entero positivo.")
                    result = applications.revise_draft(
                        database,
                        path[len("/api/drafts/") :],
                        expected,
                        applications.DraftInput.model_validate(body["draft"]),
                    )
                    self._json(HTTPStatus.OK, result)
                elif path == "/api/searches":
                    if not isinstance(body, dict) or set(body) != {"profile", "replace"}:
                        raise ValueError("Campos requeridos: profile, replace.")
                    if not isinstance(body["replace"], bool):
                        raise ValueError("replace debe ser booleano.")
                    profile = saved_searches.SavedSearch.model_validate(body["profile"])
                    saved_searches.save(database, profile, replace=body["replace"])
                    self._json(HTTPStatus.OK, profile.model_dump())
                else:
                    self._json(HTTPStatus.NOT_FOUND, {"error": "Ruta no encontrada."})
            except (StorageError, sqlite3.Error, OSError, ValueError, UnicodeError) as error:
                self._error(error)

        def do_OPTIONS(self) -> None:
            self._json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "OPTIONS no disponible."})

        def _application_write(self, *, create: bool) -> None:
            self.connection.settimeout(10)
            try:
                route = urlsplit(self.path)
                draft_create = (
                    create
                    and route.path.startswith("/api/applications/")
                    and route.path.endswith("/drafts")
                )
                draft_revision = not create and route.path.startswith("/api/drafts/")
                length = int(self.headers.get("Content-Length", ""))
                if self.headers.get("Transfer-Encoding") or not 1 <= length <= 16384:
                    raise ValueError("Cuerpo fuera de límite (1–16384 bytes).")
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError("Cuerpo incompleto.")
                if not self._host_allowed() or not self._origin_allowed():
                    return
                if (
                    route.query
                    or (create and route.path != "/api/applications" and not draft_create)
                    or (
                        not create
                        and not draft_revision
                        and not route.path.startswith("/api/applications/")
                    )
                ):
                    self._json(HTTPStatus.NOT_FOUND, {"error": "Ruta no encontrada."})
                    return
                if (
                    self.headers.get("Content-Type", "").split(";")[0].strip().lower()
                    != "application/json"
                ):
                    self._json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "Se requiere JSON."})
                    return
                body = json.loads(raw)
                if draft_create:
                    application_id = route.path[len("/api/applications/") : -len("/drafts")].rstrip(
                        "/"
                    )
                    result = applications.create_draft(
                        database, application_id, applications.DraftInput.model_validate(body)
                    )
                elif draft_revision:
                    if not isinstance(body, dict) or set(body) != {"expected_version", "draft"}:
                        raise ValueError("Campos requeridos: expected_version, draft.")
                    expected = body["expected_version"]
                    if isinstance(expected, bool) or not isinstance(expected, int) or expected < 1:
                        raise ValueError("expected_version debe ser un entero positivo.")
                    result = applications.revise_draft(
                        database,
                        route.path[len("/api/drafts/") :],
                        expected,
                        applications.DraftInput.model_validate(body["draft"]),
                    )
                elif create:
                    result = applications.create(database, applications.Create.model_validate(body))
                else:
                    result = applications.update(
                        database,
                        route.path[len("/api/applications/") :],
                        applications.Update.model_validate(body),
                    )
                self._json(HTTPStatus.OK, result)
            except (StorageError, sqlite3.Error, OSError, ValueError, UnicodeError) as error:
                self._error(error)

        def do_POST(self) -> None:
            if urlsplit(self.path).path.startswith(("/api/simulations", "/api/http-trials")):
                self._simulation_write()
                return
            self._application_write(create=True)

        def _simulation_write(self) -> None:
            http_mode = urlsplit(self.path).path.startswith("/api/http-trials")
            service = http_trial if http_mode else simulation
            resource = "http-trials" if http_mode else "simulations"
            self.connection.settimeout(2)
            try:
                length = int(self.headers.get("Content-Length", ""))
                if self.headers.get("Transfer-Encoding") or not 1 <= length <= 4096:
                    raise ValueError("Cuerpo fuera del límite permitido.")
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError("Cuerpo incompleto.")
                if not self._host_allowed() or not self._origin_allowed():
                    return
                if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                    raise ValueError("Se requiere application/json.")
                route = urlsplit(self.path)
                if route.query:
                    raise ValueError("La simulación no acepta parámetros de URL.")
                body = json.loads(raw)
                if not isinstance(body, dict):
                    raise ValueError("Se requiere un objeto JSON.")
                parts = route.path.strip("/").split("/")
                if parts == ["api", resource]:
                    if set(body) != {"draft_id", "version"} or not isinstance(
                        body["draft_id"], str
                    ):
                        raise ValueError("Campos requeridos: draft_id y version.")
                    result = service.prepare(database, body["draft_id"], body["version"])
                elif len(parts) == 4 and parts[:2] == ["api", resource]:
                    if parts[3] == "send":
                        if set(body) != {"review_sha256", "scenario"} or not all(
                            isinstance(value, str) for value in body.values()
                        ):
                            raise ValueError("Campos requeridos: review_sha256 y scenario.")
                        result = service.send(
                            database, parts[2], body["review_sha256"], body["scenario"]
                        )
                    elif parts[3] == "reconcile" and not body:
                        result = service.reconcile(database, parts[2])
                    elif parts[3] == "retry" and http_mode and set(body) == {"review_sha256"}:
                        if not isinstance(body["review_sha256"], str):
                            raise ValueError("review_sha256 debe ser texto.")
                        result = http_trial.retry(database, parts[2], body["review_sha256"])
                    else:
                        raise ValueError("Acción o campos desconocidos.")
                else:
                    self._json(HTTPStatus.NOT_FOUND, {"error": "Ruta no encontrada."})
                    return
                self._json(HTTPStatus.OK, result)
            except (StorageError, sqlite3.Error, OSError, ValueError) as error:
                self._error(error)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer((HOST, port), Handler)
    server.daemon_threads = True
    return server
