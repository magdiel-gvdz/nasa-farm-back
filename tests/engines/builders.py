"""Celdas sintéticas con un clima o un suelo extremos, para casos de resultado evidente.

Cada constructor parte de la celda sintética de Saltillo y cambia solo lo que el caso necesita,
así que el resto de los datos sigue siendo coherente con el contrato de DATA.
"""

import dataclasses

from app.data.fixture import FixtureProvider
from app.data.models import ClimatologyDecade, DailyRow, SoilLayer
from app.engines.suitability import CellData

BASE_CELL = "E9_r0463_c0846"
_WINTER_DECADES = set(range(1, 10)) | set(range(31, 37))
_SUMMER_DECADES = set(range(13, 28))


class EditedCell(FixtureProvider):
    """Proveedor con una sola celda, cuyas filas pasan por funciones de edición."""

    def __init__(self, *, climatology=None, soil=None, daily=None, indicators=None):
        super().__init__()
        self._edit = {
            "climatology": climatology,
            "soil": soil,
            "daily": daily,
            "indicators": indicators,
        }
        self._cells = {BASE_CELL: self._cells[BASE_CELL]}

    def _apply(self, name, rows):
        edit = self._edit[name]
        return tuple(edit(row) for row in rows) if edit else rows

    def climatology(self, cell_id):
        return self._apply("climatology", super().climatology(cell_id))

    def soil(self, cell_id):
        return self._apply("soil", super().soil(cell_id))

    def indicators(self, cell_id):
        return self._apply("indicators", super().indicators(cell_id))

    def daily(self, cell_id):
        series = super().daily(cell_id)
        rows = self._apply("daily", series)
        return type(series)(rows, series.origin) if rows is not series else series

    def cell_data(self) -> CellData:
        return CellData(self.climatology(BASE_CELL), self.soil(BASE_CELL))


def _frost(row: ClimatologyDecade, frost: float, hard: float) -> ClimatologyDecade:
    return dataclasses.replace(row, frost_prob=frost, frost_m2_prob=hard)


def frost_free() -> EditedCell:
    """Nunca hiela."""
    return EditedCell(
        climatology=lambda row: _frost(row, 0.0, 0.0),
        daily=lambda day: dataclasses.replace(
            day,
            tmin_adj_c=max(day.tmin_adj_c, 5.0),
            tmin_c=max(day.tmin_c, 5.0),
        ),
    )


def frozen_winters() -> EditedCell:
    """Hiela todos los inviernos, de octubre a marzo."""

    def climatology(row):
        if row.decade in _WINTER_DECADES:
            return _frost(row, 1.0, 0.8)
        return row

    return EditedCell(climatology=climatology)


def extreme_heat() -> EditedCell:
    """Todos los veranos superan los 38 °C."""

    def climatology(row):
        if row.decade in _SUMMER_DECADES:
            return dataclasses.replace(
                row, hot_prob_30=1.0, hot_prob_32=1.0, hot_prob_35=1.0, hot_prob_38=1.0
            )
        return row

    return EditedCell(climatology=climatology)


def no_rain() -> EditedCell:
    """No llueve nunca."""
    return EditedCell(
        climatology=lambda row: dataclasses.replace(
            row, precip_p10=0.0, precip_p50=0.0, precip_p90=0.0, heavy_rain_prob=0.0
        ),
        daily=lambda day: dataclasses.replace(day, precip_mm=0.0),
    )


def alkaline_soil(ph: float = 8.8) -> EditedCell:
    """Suelo muy alcalino en todas las capas."""
    return EditedCell(soil=lambda layer: dataclasses.replace(layer, ph=ph))


BUILDERS = {
    "frost_free": frost_free,
    "frozen_winters": frozen_winters,
    "extreme_heat": extreme_heat,
    "no_rain": no_rain,
    "alkaline_soil": alkaline_soil,
}

__all__ = ["BUILDERS", "ClimatologyDecade", "DailyRow", "EditedCell", "SoilLayer"]
