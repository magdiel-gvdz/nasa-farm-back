"""Validación de geometrías GeoJSON de geocercas, área geodésica y centroide."""

import math
from numbers import Real

from pyproj import Geod
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.polygon import orient

MAX_VERTICES = 2000
MAX_AREA_HA = 10_000
EXPECTED_ORDER = "[lon, lat]"

_GEOD = Geod(ellps="WGS84")


class GeometryError(ValueError):
    """La geometría no cumple las reglas; `reason` es una clave estable para el mensaje."""

    def __init__(self, reason: str, **details):
        super().__init__(reason)
        self.reason = reason
        self.details = details


def _malformed() -> GeometryError:
    return GeometryError("malformed_coordinates", expected_order=EXPECTED_ORDER)


def _position(value) -> tuple[float, float]:
    if not isinstance(value, (list, tuple)) or not 2 <= len(value) <= 3:
        raise _malformed()
    for number in value:
        if isinstance(number, bool) or not isinstance(number, Real) or not math.isfinite(number):
            raise _malformed()
    lon, lat = float(value[0]), float(value[1])
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise GeometryError(
            "coordinates_out_of_range", expected_order=EXPECTED_ORDER, position=[lon, lat]
        )
    return lon, lat


def _ring(value) -> list[tuple[float, float]]:
    ring = [_position(position) for position in value]
    if len(ring) < 4:
        raise GeometryError("ring_too_short", min_positions=4)
    if ring[0] != ring[-1]:
        raise GeometryError("ring_not_closed")
    return ring


def _polygon(value, budget: list[int]) -> Polygon:
    if not isinstance(value, (list, tuple)) or not value:
        raise _malformed()
    # Se cuenta antes de convertir cada anillo para rechazar pronto una geometría enorme.
    for ring in value:
        if not isinstance(ring, (list, tuple)):
            raise _malformed()
        budget[0] += len(ring)
        if budget[0] > MAX_VERTICES:
            raise GeometryError("too_many_vertices", max_vertices=MAX_VERTICES)
    rings = [_ring(ring) for ring in value]
    return Polygon(rings[0], rings[1:])


def parse_geometry(geometry: dict) -> Polygon | MultiPolygon:
    """Convierte un GeoJSON `Polygon` o `MultiPolygon` WGS84 válido; si no, `GeometryError`."""
    kind = geometry.get("type") if isinstance(geometry, dict) else None
    coordinates = geometry.get("coordinates") if isinstance(geometry, dict) else None
    budget = [0]
    if kind == "Polygon":
        shape = _polygon(coordinates, budget)
    elif kind == "MultiPolygon":
        if not isinstance(coordinates, (list, tuple)) or not coordinates:
            raise _malformed()
        shape = MultiPolygon([_polygon(part, budget) for part in coordinates])
    else:
        raise GeometryError("unsupported_type", allowed_types=["Polygon", "MultiPolygon"])
    if not shape.is_valid:
        raise GeometryError("self_intersection")
    if shape.is_empty or shape.area == 0:
        raise GeometryError("empty_area")
    return shape


def area_ha(shape: Polygon | MultiPolygon) -> float:
    """Área geodésica sobre el elipsoide WGS84, en hectáreas."""
    parts = shape.geoms if isinstance(shape, MultiPolygon) else [shape]
    # Exterior antihorario y huecos horarios: los huecos restan con su signo.
    total = sum(_GEOD.geometry_area_perimeter(orient(part, 1.0))[0] for part in parts)
    return abs(total) / 10_000


def centroid(shape: Polygon | MultiPolygon) -> tuple[float, float]:
    point = shape.centroid
    return point.x, point.y
