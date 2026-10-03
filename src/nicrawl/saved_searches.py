"""Perfiles locales versionados; consultas compartidas, sin modificar ofertas."""

import json
import os
import tempfile
from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from nicrawl import queries
from nicrawl.locking import CollectionBusy, collection_lock
from nicrawl.personal import Preferences, rank

Name = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,47}$")]
Text = Annotated[str, Field(max_length=120)]
Term = Annotated[str, Field(min_length=1, max_length=80)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SavedSearch(StrictModel):
    name: Name
    goal: Annotated[str, Field(max_length=240)] = ""
    view: Literal["list", "rank"] = "list"
    query: Text = ""
    title_query: Text = ""
    company: Text = ""
    source: Literal["", "remotive", "greenhouse:gitlab"] = ""
    location_text: Text = ""
    limit: Annotated[int, Field(ge=1, le=200)] = 50
    want: Annotated[list[Term], Field(max_length=20)] = Field(default_factory=list)
    avoid: Annotated[list[Term], Field(max_length=20)] = Field(default_factory=list)
    mode: Literal["remote", "hybrid", "onsite"] | None = None
    fields: list[Literal["title", "tags", "description"]] = Field(
        default=["title", "tags", "description"], max_length=3
    )
    include_dismissed: bool = False

    def preferences(self) -> Preferences:
        return Preferences(tuple(self.want), tuple(self.avoid), self.mode, tuple(self.fields))

    def filters(self) -> queries.Filters:
        return queries.Filters(
            self.query, self.company, self.source, self.location_text, self.title_query
        )

    @model_validator(mode="after")
    def validate_preferences(self) -> Self:
        if self.view == "rank" or self.want or self.avoid or self.mode:
            self.preferences().validate()
        elif len(set(self.fields)) != len(self.fields):
            raise ValueError("No repitas campos de ranking.")
        return self


class SearchBook(StrictModel):
    schema_version: Literal[1] = 1
    searches: Annotated[list[SavedSearch], Field(max_length=100)] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_names(self) -> Self:
        if len({item.name for item in self.searches}) != len(self.searches):
            raise ValueError("Nombres de búsqueda duplicados.")
        return self


def book_path(database: Path) -> Path:
    return Path(str(database.resolve()) + ".searches.json")


def read_json(path: Path, *, max_bytes: int = 1024 * 1024) -> Any:
    with path.open("rb") as stream:
        data = stream.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("Archivo JSON fuera del límite de tamaño.")
    return json.loads(data.decode("utf-8-sig"))


def list_saved(database: Path) -> SearchBook:
    path = book_path(database)
    if not path.exists():
        return SearchBook()
    return SearchBook.model_validate(read_json(path))


def get_saved(database: Path, name: str) -> SavedSearch:
    for item in list_saved(database).searches:
        if item.name == name:
            return item
    raise ValueError("Búsqueda guardada no encontrada.")


def _write_book(database: Path, book: SearchBook) -> None:
    path = book_path(database)
    if path.is_symlink() or (path.exists() and database.exists() and path.samefile(database)):
        raise ValueError("El archivo de búsquedas no puede ser un enlace a la base.")
    payload = book.model_dump_json(indent=2).encode("utf-8")
    if len(payload) > 1024 * 1024:
        raise ValueError("Máximo 1 MiB de búsquedas guardadas.")
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = stream.name
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary:
            Path(temporary).unlink(missing_ok=True)


def save(database: Path, profile: SavedSearch, *, replace: bool = False) -> SavedSearch:
    try:
        with collection_lock(book_path(database)):
            book = list_saved(database)
            exists = any(item.name == profile.name for item in book.searches)
            if exists and not replace:
                raise ValueError("Ese nombre ya existe; indicá replace para reemplazarlo.")
            items = [item for item in book.searches if item.name != profile.name]
            updated = SearchBook(searches=sorted([*items, profile], key=lambda item: item.name))
            _write_book(database, updated)
    except CollectionBusy as error:
        raise ValueError("Otra operación está actualizando las búsquedas; reintentá.") from error
    return profile


def delete(database: Path, name: str) -> None:
    try:
        with collection_lock(book_path(database)):
            get_saved(database, name)
            book = list_saved(database)
            book.searches = [item for item in book.searches if item.name != name]
            _write_book(database, book)
    except CollectionBusy as error:
        raise ValueError("Otra operación está actualizando las búsquedas; reintentá.") from error


def run_saved(database: Path, name: str) -> dict[str, Any]:
    profile = get_saved(database, name)
    if profile.view == "rank":
        return rank(
            database,
            profile.preferences(),
            filters=profile.filters(),
            limit=profile.limit,
            include_dismissed=profile.include_dismissed,
        )
    return queries.search(database, profile.filters(), limit=profile.limit)
