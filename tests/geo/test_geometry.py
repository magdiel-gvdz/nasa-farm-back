import copy
import math

import pytest
from pyproj import Geod

from app.geo.geometry import MAX_VERTICES, GeometryError, area_ha, centroid, parse_geometry
from app.i18n import MESSAGES
from tests.helpers import square

GEOD = Geod(ellps="WGS84")


def square_km(lon: float, lat: float, side_m: float) -> dict:
    """Cuadrado de lado `side_m` medido sobre el elipsoide desde su esquina suroeste."""
    east_lon, _, _ = GEOD.fwd(lon, lat, 90, side_m)
    _, north_lat, _ = GEOD.fwd(lon, lat, 0, side_m)
    ring = [[lon, lat], [east_lon, lat], [east_lon, north_lat], [lon, north_lat], [lon, lat]]
    return {"type": "Polygon", "coordinates": [ring]}


def reason(geometry) -> GeometryError:
    with pytest.raises(GeometryError) as caught:
        parse_geometry(geometry)
    return caught.value


def with_ring(ring) -> dict:
    return {"type": "Polygon", "coordinates": [ring]}


# ---------------------------------------------------------------- rechazos


@pytest.mark.parametrize(
    "geometry",
    [
        {"type": "Point", "coordinates": [-101.0, 25.4]},
        {"type": "LineString", "coordinates": [[-101.0, 25.4], [-101.1, 25.5]]},
        {"type": "polygon", "coordinates": []},
        {"coordinates": []},
    ],
)
def test_only_polygons_and_multipolygons(geometry):
    error = reason(geometry)
    assert error.reason == "unsupported_type"
    assert error.details["allowed_types"] == ["Polygon", "MultiPolygon"]


def test_open_ring():
    ring = square()["coordinates"][0][:-1]
    assert reason(with_ring(ring)).reason == "ring_not_closed"


@pytest.mark.parametrize("ring", [[], [[-101, 25], [-101.1, 25], [-101, 25]]])
def test_ring_with_too_few_points(ring):
    assert reason(with_ring(ring)).reason == "ring_too_short"


@pytest.mark.parametrize(
    "position", [[-101.0, 125.4], [25.42, -101.01], [181.0, 25.4], [-101.0, -90.5]]
)
def test_out_of_range_coordinates_hint_the_order(position):
    ring = [position, [-101.0, 25.41], [-101.0, 25.43], position]
    error = reason(with_ring(ring))
    assert error.reason == "coordinates_out_of_range"
    assert error.details["expected_order"] == "[lon, lat]"


@pytest.mark.parametrize(
    "coordinates",
    [
        [],
        "not-a-list",
        [[[-101.0], [-101.0, 25.4], [-101.1, 25.4], [-101.0]]],
        [[["-101.0", "25.4"], [-101.0, 25.4], [-101.1, 25.4], ["-101.0", "25.4"]]],
        [[[True, False], [-101.0, 25.4], [-101.1, 25.4], [True, False]]],
        [[[math.nan, 25.4], [-101.0, 25.4], [-101.1, 25.4], [math.nan, 25.4]]],
        [[[math.inf, 25.4], [-101.0, 25.4], [-101.1, 25.4], [math.inf, 25.4]]],
        [[[-101.0, 25.4, 1600, 7], [-101.0, 25.4], [-101.1, 25.4], [-101.0, 25.4, 1600, 7]]],
        [[-101.0, 25.4], [-101.1, 25.4]],
        [[None, None, None, None]],
    ],
)
def test_malformed_coordinates(coordinates):
    assert reason({"type": "Polygon", "coordinates": coordinates}).reason == "malformed_coordinates"


@pytest.mark.parametrize("coordinates", [[], None, [[]], [[[[-101.0, 25.4]]], "x"]])
def test_malformed_multipolygon(coordinates):
    error = reason({"type": "MultiPolygon", "coordinates": coordinates})
    assert error.reason in {"malformed_coordinates", "ring_too_short"}


def circle(points: int) -> list:
    ring = [
        [
            -101.0 + 0.01 * math.cos(2 * math.pi * i / points),
            25.4 + 0.01 * math.sin(2 * math.pi * i / points),
        ]
        for i in range(points)
    ]
    return [*ring, ring[0]]


def test_vertex_limit():
    assert parse_geometry(with_ring(circle(MAX_VERTICES - 1))).is_valid
    error = reason(with_ring(circle(MAX_VERTICES)))
    assert error.reason == "too_many_vertices"
    assert error.details["max_vertices"] == 2000


def test_vertex_limit_counts_every_ring_and_part():
    part = circle(1200)
    shifted = [[lon + 1, lat] for lon, lat in part]
    error = reason({"type": "MultiPolygon", "coordinates": [[part], [shifted]]})
    assert error.reason == "too_many_vertices"


def test_self_intersection():
    bow_tie = [
        [-101.02, 25.41],
        [-101.00, 25.43],
        [-101.00, 25.41],
        [-101.02, 25.43],
        [-101.02, 25.41],
    ]
    assert reason(with_ring(bow_tie)).reason == "self_intersection"


def test_overlapping_parts():
    first = square()["coordinates"]
    second = square(lon=-101.01)["coordinates"]
    error = reason({"type": "MultiPolygon", "coordinates": [first, second]})
    assert error.reason == "self_intersection"


def test_zero_area():
    line = [[-101.02, 25.41], [-101.00, 25.41], [-101.01, 25.41], [-101.02, 25.41]]
    assert reason(with_ring(line)).reason in {"self_intersection", "empty_area"}


def test_every_rejection_has_a_message_in_both_languages():
    reasons = {
        "unsupported_type",
        "malformed_coordinates",
        "coordinates_out_of_range",
        "ring_too_short",
        "ring_not_closed",
        "too_many_vertices",
        "self_intersection",
        "empty_area",
        "too_large",
    }
    assert {
        key.removeprefix("geometry.") for key in MESSAGES if key.startswith("geometry.")
    } == reasons


# ---------------------------------------------------------------- área y centroide


def test_one_kilometre_square_near_saltillo():
    geometry = square_km(-101.02, 25.41, 1000)
    shape = parse_geometry(geometry)
    assert 99 < area_ha(shape) < 101
    assert area_ha(shape) == pytest.approx(100, rel=0.001)
    lon, lat = centroid(shape)
    ring = geometry["coordinates"][0]
    assert ring[0][0] < lon < ring[1][0]
    assert ring[0][1] < lat < ring[2][1]


def test_area_does_not_depend_on_ring_orientation():
    geometry = square_km(-101.02, 25.41, 1000)
    reversed_geometry = with_ring(geometry["coordinates"][0][::-1])
    assert area_ha(parse_geometry(reversed_geometry)) == pytest.approx(
        area_ha(parse_geometry(geometry))
    )


def test_holes_are_subtracted_whatever_their_orientation():
    outer = square_km(-101.02, 25.41, 1000)["coordinates"][0]
    hole = square_km(-101.018, 25.412, 500)["coordinates"][0]
    for inner in (hole, hole[::-1]):
        shape = parse_geometry({"type": "Polygon", "coordinates": [outer, inner]})
        assert area_ha(shape) == pytest.approx(75, rel=0.005)


def test_multipolygon_of_two_parts():
    west = square_km(-101.02, 25.41, 1000)["coordinates"]
    east = square_km(-100.98, 25.41, 2000)["coordinates"]
    shape = parse_geometry({"type": "MultiPolygon", "coordinates": [west, east]})
    assert area_ha(shape) == pytest.approx(500, rel=0.002)
    lon, lat = centroid(shape)
    # El centroide pondera por superficie: queda dentro de la parte grande.
    assert east[0][0][0] < lon < east[0][1][0]
    assert east[0][0][1] < lat < east[0][2][1]


def test_altitude_is_accepted_and_ignored():
    geometry = copy.deepcopy(square())
    geometry["coordinates"][0] = [[lon, lat, 1600] for lon, lat in geometry["coordinates"][0]]
    assert area_ha(parse_geometry(geometry)) == pytest.approx(area_ha(parse_geometry(square())))
