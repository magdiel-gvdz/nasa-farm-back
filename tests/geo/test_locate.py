import pytest

from app.geo import grid
from app.geo.geometry import GeometryError
from app.geo.locate import GridLocator, OutOfRegionError
from app.geo.zones import PILOT_ZONES, BBoxCellCatalog, Zone
from tests.helpers import square

locate = GridLocator(BBoxCellCatalog())


@pytest.mark.parametrize(
    ("zone_id", "lon", "lat"),
    [
        ("coah-sureste", -101.02, 25.41),
        ("coah-laguna", -103.30, 25.60),
        ("coah-norte", -100.80, 28.30),
        ("coah-centro", -101.80, 27.00),
    ],
)
def test_one_field_per_zone(zone_id, lon, lat):
    location = locate(square(lon=lon, lat=lat))
    assert location.zone_id == zone_id
    assert location.cell_id == grid.lonlat_to_cell_id(lon + 0.01, lat + 0.01)
    assert location.centroid == (round(lon + 0.01, 6), round(lat + 0.01, 6))
    assert (location.country, location.state, location.municipality) == ("MX", "Coahuila", None)
    assert location.cell_assignment == "centroid"
    assert 400 < location.area_ha < 500


def test_field_across_two_cells_takes_the_centroid_cell():
    row, col = grid.parse_cell_id("E9_r0463_c0846")
    west_lon, lat = grid.rowcol_to_centroid(row, col)
    east_lon, _ = grid.rowcol_to_centroid(row, col + 1)
    boundary = (west_lon + east_lon) / 2
    # 30 % de la geocerca en la celda oeste y 70 % en la celda este.
    ring = [
        [boundary - 0.003, lat],
        [boundary + 0.007, lat],
        [boundary + 0.007, lat + 0.005],
        [boundary - 0.003, lat + 0.005],
        [boundary - 0.003, lat],
    ]
    location = locate({"type": "Polygon", "coordinates": [ring]})
    assert grid.lonlat_to_cell_id(ring[0][0], lat) == "E9_r0463_c0846"
    assert location.cell_id == "E9_r0463_c0847"
    assert location.cell_assignment == "centroid"


def test_nevada_is_out_of_region():
    with pytest.raises(OutOfRegionError) as caught:
        locate(square(lon=-117.02, lat=39.41))
    assert caught.value.zones == PILOT_ZONES
    assert caught.value.cell_id == grid.lonlat_to_cell_id(-117.01, 39.42)


def test_just_outside_a_zone_is_out_of_region():
    with pytest.raises(OutOfRegionError):
        locate(square(lon=-100.55, lat=25.41))


def test_oversized_field_is_invalid_before_checking_the_region():
    with pytest.raises(GeometryError) as caught:
        locate(square(lon=-117.0, lat=39.0, side_deg=0.2))
    assert caught.value.reason == "too_large"
    assert caught.value.details["max_area_ha"] == 10_000
    assert caught.value.details["area_ha"] > 10_000


def test_field_just_under_the_area_limit_is_accepted():
    location = locate(square(lon=-101.25, lat=25.35, side_deg=0.09))
    assert 9_000 < location.area_ha <= 10_000
    assert location.zone_id == "coah-sureste"


def test_invalid_geometry_is_reported_before_locating():
    with pytest.raises(GeometryError):
        locate({"type": "Point", "coordinates": [-101.0, 25.4]})


def test_the_catalog_decides_coverage():
    class OnlyNevada:
        zone = Zone("us-nv", "Nevada", "Nevada", "US", (), (-118.0, 39.0, -116.0, 40.0))

        def zones(self):
            return (self.zone,)

        def zone_of(self, cell_id):
            return self.zone if cell_id == grid.lonlat_to_cell_id(-117.01, 39.42) else None

    nevada = GridLocator(OnlyNevada())
    location = nevada(square(lon=-117.02, lat=39.41))
    assert (location.zone_id, location.country, location.state) == ("us-nv", "US", "Nevada")
    with pytest.raises(OutOfRegionError):
        nevada(square())
