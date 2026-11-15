"""Proveedor de datos sintéticos; sus archivos los genera `scripts/build_fixtures.py`."""

import json
from collections.abc import Sequence
from functools import cache
from importlib import resources

from app.data import synthetic
from app.data.models import (
    Cell,
    ClimatologyDecade,
    DailyRow,
    IndicatorDecade,
    IndicatorYear,
    SoilLayer,
    Source,
    Zone,
)
from app.data.provider import UnknownCellError

DATA_VERSION = "fixture"
FIXTURE_FILES = ("cells", "climatology", "indicators", "years", "soil", "sources")


def _load(name: str) -> list[dict]:
    text = resources.files("app.data.fixtures").joinpath(f"{name}.json").read_text("utf-8")
    return json.loads(text)


def _by_cell(model: type, name: str) -> dict[str, tuple]:
    grouped: dict[str, list] = {}
    for row in _load(name):
        grouped.setdefault(row["cell_id"], []).append(model(**row))
    return {cell_id: tuple(rows) for cell_id, rows in grouped.items()}


@cache
def _daily(cell_id: str) -> tuple[DailyRow, ...]:
    return tuple(DailyRow(**row) for row in synthetic.daily_rows(cell_id))


class FixtureProvider:
    """Dos celdas (Saltillo y La Laguna), 2016-2025. Determinista y sin acceso a AWS."""

    def __init__(self) -> None:
        self._cells = {row["cell_id"]: Cell(**row) for row in _load("cells")}
        self._climatology = _by_cell(ClimatologyDecade, "climatology")
        self._indicators = _by_cell(IndicatorDecade, "indicators")
        self._years = _by_cell(IndicatorYear, "years")
        self._soil = _by_cell(SoilLayer, "soil")
        self._sources = tuple(Source(**row) for row in _load("sources"))

    def is_ready(self) -> bool:
        return True

    def data_version(self) -> str | None:
        return DATA_VERSION

    def cells(self) -> Sequence[Cell]:
        return tuple(self._cells.values())

    def zones(self) -> Sequence[Zone]:
        zones: dict[str, Zone] = {}
        for cell in self._cells.values():
            known = zones.get(cell.zone_id)
            zones[cell.zone_id] = Zone(
                cell.zone_id, cell.zone_name, known.n_cells + 1 if known else 1
            )
        return tuple(zones.values())

    def cell(self, cell_id: str) -> Cell:
        try:
            return self._cells[cell_id]
        except KeyError:
            raise UnknownCellError(cell_id) from None

    def climatology(self, cell_id: str) -> Sequence[ClimatologyDecade]:
        return self._rows(self._climatology, cell_id)

    def indicators(self, cell_id: str) -> Sequence[IndicatorDecade]:
        return self._rows(self._indicators, cell_id)

    def years(self, cell_id: str) -> Sequence[IndicatorYear]:
        return self._rows(self._years, cell_id)

    def soil(self, cell_id: str) -> Sequence[SoilLayer]:
        return self._rows(self._soil, cell_id)

    def sources(self) -> Sequence[Source]:
        return self._sources

    def daily(self, cell_id: str) -> Sequence[DailyRow]:
        self.cell(cell_id)
        return _daily(cell_id)

    def _rows(self, table: dict[str, tuple], cell_id: str) -> tuple:
        self.cell(cell_id)
        return table.get(cell_id, ())
