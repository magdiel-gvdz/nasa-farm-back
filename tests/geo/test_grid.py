"""Malla EASE-Grid 2.0 de 9 km.

Las siete primeras pruebas son las que describe docs/fuentes_de_datos.md §4 para
`ingest/common/grid.py` de DATA: esquinas globales, cruce del ecuador, ida y vuelta del
centroide, unicidad y conteo por zona.

`data/cells.csv` reproduce las 136 celdas con la regla publicada por DATA (centroide dentro
del recuadro de la zona). Cuando DATA comparta su CSV, sustituye a este archivo sin cambiar
las pruebas.
"""

import csv
from pathlib import Path

import pytest

from app.geo import grid
from app.geo.zones import PILOT_ZONES, BBoxCellCatalog

CELLS = list(csv.DictReader((Path(__file__).parent / "data" / "cells.csv").open(encoding="utf-8")))
EXPECTED_COUNTS = {"coah-sureste": 45, "coah-laguna": 35, "coah-norte": 20, "coah-centro": 36}


def test_grid_width_matches_the_projection_extent():
    assert grid.N_COLS * grid.CELL_M == pytest.approx(2 * abs(grid.X0), abs=1e-3)
    assert grid.N_ROWS * grid.CELL_M == pytest.approx(2 * grid.Y0, abs=1e-3)


def test_upper_left_corner_is_the_first_cell():
    assert grid.lonlat_to_rowcol(-179.999, 85.04) == (0, 0)
    assert grid.lonlat_to_cell_id(-179.999, 85.04) == "E9_r0000_c0000"


def test_lower_right_corner_is_the_last_cell():
    assert grid.lonlat_to_rowcol(179.999, -85.04) == (grid.N_ROWS - 1, grid.N_COLS - 1)
    assert grid.lonlat_to_rowcol(180, -85.04) == (grid.N_ROWS - 1, grid.N_COLS - 1)
    assert grid.lonlat_to_cell_id(179.999, -85.04) == "E9_r1623_c3855"


def test_equator_and_prime_meridian_split_the_grid_in_halves():
    assert grid.lonlat_to_rowcol(-1e-6, 1e-6) == (811, 1927)
    assert grid.lonlat_to_rowcol(1e-6, -1e-6) == (812, 1928)


def test_centroid_round_trip():
    for row, col in [(0, 0), (811, 1927), (463, 846), (1623, 3855), (120, 3001)]:
        lon, lat = grid.rowcol_to_centroid(row, col)
        assert grid.lonlat_to_rowcol(lon, lat) == (row, col)
        assert grid.parse_cell_id(grid.cell_id(row, col)) == (row, col)


def test_cell_ids_are_unique():
    catalog = BBoxCellCatalog()
    ids = catalog.cell_ids()
    assert len(ids) == len(set(ids)) == 136
    # Ninguna celda pertenece a dos zonas.
    per_zone = [len(grid.cells_in_bbox(*zone.bbox)) for zone in PILOT_ZONES]
    assert sum(per_zone) == len(ids)


def test_cell_count_per_zone_matches_data():
    counts = {zone.zone_id: len(grid.cells_in_bbox(*zone.bbox)) for zone in PILOT_ZONES}
    assert counts == EXPECTED_COUNTS


def test_published_cells_recompute_from_their_centroids():
    assert len(CELLS) == 136
    catalog = BBoxCellCatalog()
    for cell in CELLS:
        computed = grid.lonlat_to_cell_id(float(cell["lon"]), float(cell["lat"]))
        assert computed == cell["cell_id"]
        assert computed == f"E9_r{int(cell['row']):04d}_c{int(cell['col']):04d}"
        assert catalog.zone_of(computed).zone_id == cell["zone_id"]
    assert {cell["cell_id"] for cell in CELLS} == set(catalog.cell_ids())


def test_saltillo_falls_in_the_reference_cell():
    assert grid.lonlat_to_cell_id(-101.0, 25.42) == "E9_r0463_c0846"


@pytest.mark.parametrize(("lon", "lat"), [(0, 89.9), (0, -89.9), (10, 85.1)])
def test_polar_latitudes_are_outside_the_grid(lon, lat):
    with pytest.raises(grid.OutsideGridError):
        grid.lonlat_to_rowcol(lon, lat)


@pytest.mark.parametrize("value", ["E9_r463_c846", "E9_r9999_c0000", "r0463_c0846", ""])
def test_malformed_cell_ids_are_rejected(value):
    with pytest.raises(ValueError):
        grid.parse_cell_id(value)
