"""Malla EASE-Grid 2.0 global de 9 km, con las mismas constantes que el pipeline de DATA.

Referencia: docs/fuentes_de_datos.md §4 (`ingest/common/grid.py` en el repositorio de DATA).
"""

import math
import re
import threading

from pyproj import Transformer

EPSG = 6933
N_COLS = 3856
N_ROWS = 1624
CELL_M = 9008.055210146
X0 = -17367530.44516138
Y0 = 7314540.830638

_CELL_ID = re.compile(r"^E9_r(\d{4})_c(\d{4})$")


class OutsideGridError(ValueError):
    """La coordenada queda fuera de la extensión de la malla (latitudes polares)."""


_local = threading.local()


def _transformers() -> tuple[Transformer, Transformer]:
    """Directa e inversa, una pareja por hilo: las rutas se ejecutan en un grupo de hilos."""
    if not hasattr(_local, "pair"):
        _local.pair = (
            Transformer.from_crs(4326, EPSG, always_xy=True),
            Transformer.from_crs(EPSG, 4326, always_xy=True),
        )
    return _local.pair


def lonlat_to_rowcol(lon: float, lat: float) -> tuple[int, int]:
    x, y = _transformers()[0].transform(lon, lat)
    if not (math.isfinite(x) and math.isfinite(y)):
        raise OutsideGridError(f"Coordenada no proyectable: {lon}, {lat}")
    row = math.floor((Y0 - y) / CELL_M)
    col = math.floor((x - X0) / CELL_M)
    if col == N_COLS and lon >= 180:
        col = N_COLS - 1  # El meridiano 180 pertenece a la última columna.
    if not (0 <= row < N_ROWS and 0 <= col < N_COLS):
        raise OutsideGridError(f"Coordenada fuera de la malla: {lon}, {lat}")
    return row, col


def cell_id(row: int, col: int) -> str:
    if not (0 <= row < N_ROWS and 0 <= col < N_COLS):
        raise OutsideGridError(f"Celda fuera de la malla: fila {row}, columna {col}")
    return f"E9_r{row:04d}_c{col:04d}"


def parse_cell_id(value: str) -> tuple[int, int]:
    match = _CELL_ID.match(value)
    if not match:
        raise ValueError(f"Identificador de celda inválido: {value!r}")
    row, col = int(match.group(1)), int(match.group(2))
    cell_id(row, col)
    return row, col


def lonlat_to_cell_id(lon: float, lat: float) -> str:
    return cell_id(*lonlat_to_rowcol(lon, lat))


def rowcol_to_centroid(row: int, col: int) -> tuple[float, float]:
    """Centroide `(lon, lat)` de la celda."""
    cell_id(row, col)
    x = X0 + (col + 0.5) * CELL_M
    y = Y0 - (row + 0.5) * CELL_M
    lon, lat = _transformers()[1].transform(x, y)
    return lon, lat


def cells_in_bbox(
    lon_min: float, lat_min: float, lon_max: float, lat_max: float
) -> list[tuple[int, int]]:
    """Celdas cuyo centroide cae dentro del recuadro, que es la regla de zona de DATA."""
    row_top, col_left = lonlat_to_rowcol(lon_min, lat_max)
    row_bottom, col_right = lonlat_to_rowcol(lon_max, lat_min)
    cells = []
    for row in range(row_top, row_bottom + 1):
        for col in range(col_left, col_right + 1):
            lon, lat = rowcol_to_centroid(row, col)
            if lon_min <= lon <= lon_max and lat_min <= lat <= lat_max:
                cells.append((row, col))
    return cells
