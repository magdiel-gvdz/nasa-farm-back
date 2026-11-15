import dataclasses
import json
import urllib.error

import pytest

from app.data.athena import AthenaProvider, DailyUnavailableError
from app.data.fixture import FixtureProvider
from app.data.models import Cell
from app.data.power import (
    PARAMETERS,
    POWER_LIVE_SOURCE,
    LocalCache,
    PowerClient,
    PowerDailySource,
    PowerUnavailableError,
    cache_key,
    to_daily_rows,
)
from app.profile.builder import build_profile
from tests.data.test_athena_provider import SALTILLO, FakeExecutor, FakeVersions

BOX = (25.5, -101.25)


def recorded_response(box_elevation=1712.0, days=("20160101", "20160102", "20160103")) -> dict:
    """Forma de la respuesta del endpoint diario por punto de NASA POWER."""
    values = {
        "T2M_MAX": [18.4, -999.0, 20.1],
        "T2M_MIN": [2.0, 1.5, -1.0],
        "T2M": [10.2, 9.0, 9.5],
        "PRECTOTCORR": [0.0, 12.3, -999.0],
        "ALLSKY_SFC_SW_DWN": [15.1, 9.8, 16.0],
        "RH2M": [40.0, 80.2, 35.5],
        "WS2M": [2.1, 3.4, 1.9],
        "WS10M_MAX": [8.2, 11.6, 6.0],
    }
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [BOX[1], BOX[0], box_elevation]},
        "properties": {
            "parameter": {
                name: dict(zip(days, series, strict=True)) for name, series in values.items()
            }
        },
    }


def cell(**changes) -> Cell:
    base = Cell(
        cell_id="E9_r0463_c0846",
        zone_id="coah-sureste",
        zone_name="Sureste",
        lat=25.41,
        lon=-100.97,
        geometry_wkt="POLYGON EMPTY",
        cell_elev_m=2112.0,
        cell_elev_source="copernicus_dem_glo90",
        power_cell_lat=BOX[0],
        power_cell_lon=BOX[1],
        power_elev_m=1712.0,
        climate_shared_by_n_cells=20,
    )
    return dataclasses.replace(base, **changes)


class Downloads:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.urls = []

    def __call__(self, url):
        self.urls.append(url)
        # Sin respuestas grabadas, el servidor no responde.
        response = self.responses.pop(0) if self.responses else TimeoutError("20 s")
        if isinstance(response, Exception):
            raise response
        return json.dumps(response).encode()


@pytest.fixture
def cache(tmp_path):
    return LocalCache(tmp_path)


# ---------------------------------------------------------------- cliente


def test_request_asks_for_the_agreed_parameters(cache):
    client = PowerClient(cache, first_year=2016, last_year=2025, download=Downloads())
    url = client.url(*BOX)
    for part in (
        "community=AG",
        "time-standard=UTC",
        "start=20160101",
        "end=20251231",
        "latitude=25.5",
    ):
        assert part in url
    assert ",".join(PARAMETERS).replace(",", "%2C") in url


def test_one_retry_with_a_pause_then_unavailable(cache):
    pauses = []
    failing = Downloads(urllib.error.URLError("timeout"), TimeoutError("20 s"))
    client = PowerClient(cache, last_year=2025, download=failing, sleep=pauses.append)
    with pytest.raises(PowerUnavailableError):
        client.raw(*BOX)
    assert len(failing.urls) == 2 and pauses == [2]
    recovering = Downloads(urllib.error.URLError("reset"), recorded_response())
    client = PowerClient(cache, last_year=2025, download=recovering, sleep=pauses.append)
    assert "properties" in client.raw(*BOX)


def test_two_cells_of_the_same_box_download_once_and_the_cache_survives_restarts(cache):
    downloads = Downloads(recorded_response())
    source = PowerDailySource(PowerClient(cache, last_year=2025, download=downloads))
    low, _ = source.daily(cell(cell_elev_m=1712.0))
    high, _ = source.daily(cell(cell_id="E9_r0463_c0847", cell_elev_m=2112.0))
    assert len(downloads.urls) == 1
    assert low[0].tmin_adj_c == 2.0 and high[0].tmin_adj_c == pytest.approx(-0.6)
    restarted = PowerDailySource(PowerClient(cache, last_year=2025, download=Downloads()))
    assert restarted.daily(cell())[0][0].tmin_c == 2.0


def test_cache_key_uses_the_exact_box_coordinates_period_and_parameters():
    key = cache_key(25.5, -101.25, 2016, 2025)
    assert key.startswith("cache/power/25.5_-101.25_2016-2025_")
    assert key != cache_key(25.5, -101.875, 2016, 2025)
    assert key != cache_key(25.5, -101.25, 1991, 2025)


# ---------------------------------------------------------------- conversión


def test_cell_400_m_above_the_box_is_0_6_degrees_colder():
    rows, adjusted = to_daily_rows(recorded_response(), cell(cell_elev_m=2112.0))
    assert adjusted and rows[0].tmin_c == 2.0 and rows[0].tmin_adj_c == pytest.approx(-0.6)
    assert rows[0].temp_adj_applied is True


def test_unknown_elevation_leaves_temperatures_unadjusted():
    rows, adjusted = to_daily_rows(recorded_response(), cell(cell_elev_m=None))
    assert not adjusted and rows[0].tmin_adj_c == rows[0].tmin_c
    rows, adjusted = to_daily_rows(recorded_response(box_elevation=None), cell())
    assert not adjusted


def test_fill_values_become_none_and_dates_are_iso():
    rows, _ = to_daily_rows(recorded_response(), cell())
    assert [row.date for row in rows] == ["2016-01-01", "2016-01-02", "2016-01-03"]
    assert rows[1].tmax_c is None and rows[1].tmax_adj_c is None
    assert rows[2].precip_mm is None and rows[1].precip_mm == 12.3
    assert rows[0].wind_max_ms == 8.2 and rows[0].gwetroot_frac is None


# ---------------------------------------------------------------- precedencia en el proveedor


def provider_with(executor, power):
    provider = AthenaProvider(executor, FakeVersions(), power=power)
    provider.refresh()
    return provider


def test_published_view_wins_and_is_marked_gold(cache):
    downloads = Downloads()
    provider = provider_with(
        FakeExecutor(), PowerDailySource(PowerClient(cache, download=downloads))
    )
    series = provider.daily(SALTILLO)
    assert series.origin == "gold" and downloads.urls == []
    assert "power_live" not in {source.source_id for source in provider.sources()}


def test_missing_view_falls_back_to_power_and_lists_its_source(cache):
    executor = FakeExecutor()
    executor.failures["v_cell_daily"] = RuntimeError(
        "TABLE_NOT_FOUND: Table v_cell_daily does not exist"
    )
    downloads = Downloads(recorded_response())
    provider = provider_with(
        executor, PowerDailySource(PowerClient(cache, last_year=2025, download=downloads))
    )
    series = provider.daily(SALTILLO)
    assert series.origin == "power_live" and len(series) == 3
    sources = {source.source_id: source for source in provider.sources()}
    assert sources["power_live"] == POWER_LIVE_SOURCE
    assert (
        sources["power_live"].data_class == "model"
        and "estimación" in sources["power_live"].used_for
    )


@pytest.mark.parametrize("error", ["Access denied", "Rate exceeded"])
def test_permission_or_transient_errors_do_not_fall_back(cache, error):
    executor = FakeExecutor()
    executor.failures["v_cell_daily"] = RuntimeError(error)
    downloads = Downloads(recorded_response())
    provider = provider_with(executor, PowerDailySource(PowerClient(cache, download=downloads)))
    with pytest.raises(DailyUnavailableError, match=error):
        provider.daily(SALTILLO)
    assert downloads.urls == []


def test_missing_view_and_power_down_is_daily_unavailable_but_the_profile_answers(cache):
    executor = FakeExecutor()
    executor.failures["v_cell_daily"] = RuntimeError("Table v_cell_daily does not exist")
    failing = Downloads(TimeoutError("20 s"), TimeoutError("20 s"))
    client = PowerClient(cache, last_year=2025, download=failing, sleep=lambda _: None)
    provider = provider_with(executor, PowerDailySource(client))
    with pytest.raises(DailyUnavailableError):
        provider.daily(SALTILLO)
    profile = build_profile(provider, SALTILLO, "es")
    assert profile["status"] == "ready"
    assert "no_daily_series" in {gap["code"] for gap in profile["gaps"]}


def test_synthetic_series_says_so():
    series = FixtureProvider().daily("E9_r0463_c0846")
    assert series.origin == "synthetic" and series[0].date == "2016-01-01"
