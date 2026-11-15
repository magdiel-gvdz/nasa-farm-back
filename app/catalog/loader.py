"""Carga y valida `data/crops.yaml`. La aplicación no arranca con un catálogo inválido."""

from collections.abc import Iterator
from pathlib import Path

import yaml
from pydantic import ValidationError

from app.catalog.models import REQUIRED_ROLES, Crop

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "crops.yaml"


class CatalogError(ValueError):
    """El catálogo no se puede usar; el mensaje nombra el cultivo y el campo."""


class Catalog:
    def __init__(self, crops: list[Crop]):
        self._by_id: dict[str, Crop] = {}
        for crop in crops:
            if crop.id in self._by_id:
                raise CatalogError(f"Identificador de cultivo repetido: {crop.id!r}")
            self._by_id[crop.id] = crop
        missing = [
            role
            for role in REQUIRED_ROLES
            if not any(role in crop.roles for crop in self._by_id.values())
        ]
        if missing:
            raise CatalogError(f"Ningún cultivo cubre estos roles: {', '.join(missing)}")

    def __iter__(self) -> Iterator[Crop]:
        return iter(self._by_id.values())

    def __len__(self) -> int:
        return len(self._by_id)

    def get(self, crop_id: str) -> Crop | None:
        return self._by_id.get(crop_id)

    def with_role(self, role: str) -> list[Crop]:
        return [crop for crop in self if role in crop.roles]


def _problem(error: dict) -> str:
    field = ".".join(str(part) for part in error["loc"])
    message = error["msg"].removeprefix("Value error, ")
    # Los validadores del modelo ya nombran el campo al principio del mensaje.
    return f"{field}: {message}" if field else message


def parse_catalog(entries: object) -> Catalog:
    if not isinstance(entries, list) or not entries:
        raise CatalogError("El catálogo debe ser una lista de cultivos con al menos uno")
    crops = []
    for position, entry in enumerate(entries, start=1):
        label = entry.get("id") if isinstance(entry, dict) else None
        try:
            crops.append(Crop.model_validate(entry))
        except ValidationError as error:
            problems = "; ".join(_problem(detail) for detail in error.errors())
            raise CatalogError(f"Cultivo {label or f'#{position}'!r}: {problems}") from None
    return Catalog(crops)


def load_catalog(path: Path = DEFAULT_PATH) -> Catalog:
    try:
        entries = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise CatalogError(f"No se pudo leer {path}: {error}") from error
    return parse_catalog(entries)
