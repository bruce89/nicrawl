"""Exportación UTF-8 transaccional a un archivo local del mismo volumen."""

import csv
import json
import os
import tempfile
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any

FIELDS = (
    "job_key",
    "source_id",
    "source_job_id",
    "source_url",
    "title",
    "company",
    "description_text",
    "location_raw",
    "salary_raw",
    "work_mode",
    "employment_type_raw",
    "tags",
    "published_raw",
    "published_at",
    "source_updated_at",
    "first_seen_at",
    "last_seen_at",
    "last_changed_at",
    "stale",
)


def csv_cell(value: Any) -> str:
    text = (
        json.dumps(value, ensure_ascii=False)
        if isinstance(value, (list, dict))
        else ""
        if value is None
        else str(value)
    )
    index = 0
    control = False
    while index < len(text) and (
        text[index].isspace() or unicodedata.category(text[index]).startswith("C")
    ):
        control |= unicodedata.category(text[index]).startswith("C")
        index += 1
    if text[index:].startswith(("=", "+", "-", "@")) or control:
        return "'" + text
    return text


def _write(stream: IO[str], report: dict[str, Any], format: str) -> None:
    if format == "json":
        json.dump(report, stream, ensure_ascii=True, indent=2)
        stream.write("\n")
    elif format == "csv":
        writer = csv.writer(stream)
        writer.writerow(FIELDS)
        for job in report["jobs"]:
            writer.writerow(csv_cell(job[field]) for field in FIELDS)
    else:
        raise ValueError("Formato desconocido.")


def export_file(
    report: dict[str, Any],
    destination: Path,
    *,
    format: str,
    overwrite: bool = False,
    database: Path,
) -> None:
    destination = destination.absolute()
    db = database.resolve()
    protected = [db, *(Path(str(db) + suffix) for suffix in ("-wal", "-shm", "-journal", ".lock"))]
    if any(
        destination.resolve() == path
        or (destination.exists() and path.exists() and destination.samefile(path))
        for path in protected
    ):
        raise ValueError("El destino no puede ser la base ni sus archivos auxiliares.")
    if destination.is_symlink():
        raise ValueError("El destino no puede ser un enlace simbólico.")
    if destination.exists() and not overwrite:
        raise FileExistsError("El destino existe; usar --overwrite para reemplazarlo.")
    name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=destination.parent,
            delete=False,
            prefix=".nicrawl-",
            suffix=".tmp",
        ) as stream:
            name = stream.name
            _write(stream.file, {**report, "exported_at": datetime.now(UTC).isoformat()}, format)
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(name, destination)
        else:
            # Publicación exclusiva: también rechaza destinos creados durante la escritura.
            os.link(name, destination)
    finally:
        if name is not None:
            Path(name).unlink(missing_ok=True)
