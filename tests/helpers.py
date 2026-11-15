import copy
import re
from functools import cache

ORIGIN = "http://localhost:5173"
SNAKE_CASE = re.compile(r"^[a-z][a-z0-9_]*$")


def square(lon: float = -101.02, lat: float = 25.41, side_deg: float = 0.02) -> dict:
    """Cuadrado GeoJSON; por defecto cae en la celda de Saltillo `E9_r0463_c0846`."""
    east, north = round(lon + side_deg, 6), round(lat + side_deg, 6)
    ring = [[lon, lat], [east, lat], [east, north], [lon, north], [lon, lat]]
    return {"type": "Polygon", "coordinates": [ring]}


def field_payload(**overrides) -> dict:
    return {"name": "Rancho Los Nogales - Parcela 1", "geometry": square(), **overrides}


def keys(node):
    """Todas las claves de un JSON, a cualquier profundidad."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from keys(value)
    elif isinstance(node, list):
        for value in node:
            yield from keys(value)


@cache
def _reference_profile() -> dict:
    from app.data.fixture import FixtureProvider
    from app.profile.builder import build_profile

    profile = build_profile(FixtureProvider(), "E9_r0463_c0846", "es")
    return {**profile, "field_id": "fld_01KA0Z5T9M3X8Q2W4E6R7T8Y9A"}


def reference_profile() -> dict:
    """Copia nueva del perfil de la celda de Saltillo con datos sintéticos."""
    return copy.deepcopy(_reference_profile())
