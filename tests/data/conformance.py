"""Comprobaciones que debe pasar cualquier implementación de `DataProvider`."""

import dataclasses
import math

import pytest

from app.data import DataProvider, UnknownCellError

UNKNOWN_CELL = "E9_r0001_c0001"
FILL_VALUES = {-999, -9999}


def _values(rows):
    for row in rows:
        yield from dataclasses.astuple(row)


def check_provider(provider: DataProvider) -> None:
    assert provider.is_ready()
    assert provider.data_version()
    cells = provider.cells()
    assert cells
    assert {zone.zone_id for zone in provider.zones()} == {cell.zone_id for cell in cells}
    assert sum(zone.n_cells for zone in provider.zones()) == len(cells)

    for cell in cells:
        cell_id = cell.cell_id
        assert provider.cell(cell_id) == cell
        climatology = provider.climatology(cell_id)
        assert [row.decade for row in climatology] == list(range(1, 37))
        assert all(row.month == (row.decade - 1) // 3 + 1 for row in climatology)

        indicators = provider.indicators(cell_id)
        keys = [(row.year, row.decade) for row in indicators]
        assert keys == sorted(set(keys))
        years = provider.years(cell_id)
        assert [row.year for row in years] == sorted({year for year, _ in keys})

        soil = provider.soil(cell_id)
        assert [row.depth_top_cm for row in soil] == sorted(row.depth_top_cm for row in soil)
        daily = provider.daily(cell_id)
        assert [row.date for row in daily] == sorted({row.date for row in daily})

        every_row = [*climatology, *indicators, *years, *soil, *daily]
        assert all(row.cell_id == cell_id and row.zone_id == cell.zone_id for row in every_row)
        for value in _values([cell, *every_row]):
            # Un dato faltante es `None`: ni valores de relleno ni NaN.
            if isinstance(value, int | float) and not isinstance(value, bool):
                assert value not in FILL_VALUES
                assert not math.isnan(value)

    sources = provider.sources()
    assert len({source.source_id for source in sources}) == len(sources) > 0
    for source in sources:
        for column in ("name", "organization", "resolution", "period", "license", "data_class"):
            assert getattr(source, column)

    for query in (
        provider.cell,
        provider.climatology,
        provider.indicators,
        provider.years,
        provider.soil,
        provider.daily,
    ):
        with pytest.raises(UnknownCellError):
            query(UNKNOWN_CELL)
