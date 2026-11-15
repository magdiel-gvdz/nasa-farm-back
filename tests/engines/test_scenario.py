import time
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.data import DataUnavailableError
from app.data.fixture import FixtureProvider
from app.engines.indicators import (
    decade_totals,
    et0_hargreaves,
    extraterrestrial_radiation,
    recompute_climatology,
)
from app.engines.scenario import NOT_RECOMPUTED, Scenario, ScenarioService
from app.engines.suitability import CellData
from app.main import create_app
from tests.helpers import MAIZE_FALLOW, field_payload

SALTILLO = "E9_r0463_c0846"
LA_LAGUNA = "E9_r0461_c0822"
PROBABILITIES = (
    "frost_prob",
    "frost_m2_prob",
    "hot_prob_30",
    "hot_prob_32",
    "hot_prob_35",
    "hot_prob_38",
    "heavy_rain_prob",
)


@pytest.fixture(scope="module")
def provider():
    return FixtureProvider()


def climate(provider, cell_id, delta_t=0.0, delta_p=0.0):
    years = [row.year for row in provider.years(cell_id)]
    return recompute_climatology(
        provider.climatology(cell_id),
        provider.daily(cell_id),
        provider.cell(cell_id).lat,
        years,
        delta_t,
        delta_p,
    )


# ---------------------------------------------------------------- indicadores


def test_extraterrestrial_radiation_matches_the_fao56_example():
    # FAO-56, ejemplo 8: 20° S, 3 de septiembre (día 246) → Ra = 32.2 MJ/m²/día.
    assert extraterrestrial_radiation(-20, 246) == pytest.approx(32.2, rel=0.02)


def test_hargreaves_grows_with_temperature_and_range():
    day = date(2020, 6, 15)
    base = et0_hargreaves(25.4, day, 30, 15, 22.5)
    assert 4 < base < 8
    assert et0_hargreaves(25.4, day, 32, 17, 24.5) > base
    assert et0_hargreaves(25.4, day, 30, 30, 30) == 0


def test_decade_totals_count_events_per_year_and_decade(provider):
    totals = decade_totals(provider.daily(SALTILLO), 25.41, [2016])
    january = totals[(2016, 1)]
    days = [
        r
        for r in provider.daily(SALTILLO)
        if r.date.startswith("2016-01-") and r.date <= "2016-01-10"
    ]
    assert january["frost"] == sum(r.tmin_adj_c < 0 for r in days)
    assert january["precip"] == pytest.approx(sum(r.precip_mm for r in days))
    assert {year for year, _ in totals} == {2016}
    warmer = decade_totals(provider.daily(SALTILLO), 25.41, [2016], delta_t_c=2)[(2016, 1)]
    assert warmer["frost"] <= january["frost"] and warmer["et0"] > january["et0"]


@pytest.mark.parametrize("cell_id", [SALTILLO, LA_LAGUNA])
def test_zero_deltas_reproduce_the_published_climatology(provider, cell_id):
    recomputed = {row.decade: row for row in climate(provider, cell_id)}
    for published in provider.climatology(cell_id):
        row = recomputed[published.decade]
        for column in PROBABILITIES:
            assert abs(getattr(row, column) - getattr(published, column)) <= 0.1, (
                column,
                row.decade,
            )
        assert row.precip_p50 == pytest.approx(published.precip_p50, abs=0.5)
        assert row.et0_p50 == pytest.approx(published.et0_p50, rel=0.02)
        assert row.ws_prob == published.ws_prob and row.smp_p50 == published.smp_p50


# ---------------------------------------------------------------- escenario


@pytest.mark.parametrize("cell_id", [SALTILLO, LA_LAGUNA])
def test_warmer_scenario_never_lowers_heat_nor_raises_frost(provider, cell_id):
    base = {row.decade: row for row in climate(provider, cell_id)}
    for row in climate(provider, cell_id, delta_t=2):
        reference = base[row.decade]
        for threshold in (30, 32, 35, 38):
            assert getattr(row, f"hot_prob_{threshold}") >= getattr(
                reference, f"hot_prob_{threshold}"
            )
        assert row.frost_prob <= reference.frost_prob
        assert row.frost_m2_prob <= reference.frost_m2_prob
        assert row.et0_p50 >= reference.et0_p50


def test_drier_scenario_lowers_rain(provider):
    base = {row.decade: row for row in climate(provider, SALTILLO)}
    for row in climate(provider, SALTILLO, delta_p=-20):
        assert row.precip_p50 == pytest.approx(base[row.decade].precip_p50 * 0.8, abs=0.01)
        assert row.heavy_rain_prob <= base[row.decade].heavy_rain_prob


def test_scenarios_are_rounded_to_the_control_steps():
    assert Scenario(1.8, -17).rounded() == Scenario(2.0, -15)
    assert Scenario(0.2, 2).is_zero


def test_zero_scenario_uses_the_published_data_without_recomputing(provider):
    service = ScenarioService(provider)
    base = CellData(provider.climatology(SALTILLO), provider.soil(SALTILLO))
    result = service.apply(SALTILLO, base, Scenario())
    assert result.cell_data is base and service.computations == 0
    assert result.describe("es")["daily_origin"] is None


def test_same_scenario_is_served_from_the_cache(provider):
    service = ScenarioService(provider)
    base = CellData(provider.climatology(SALTILLO), provider.soil(SALTILLO))
    first = service.apply(SALTILLO, base, Scenario(2, -20))
    second = service.apply(SALTILLO, base, Scenario(2.1, -19))
    assert second is first and service.computations == 1
    described = first.describe("en")
    assert described["daily_origin"] == "synthetic"
    assert set(described["not_recomputed"]) == set(NOT_RECOMPUTED)
    assert {"soil_moisture", "bare_soil"} <= set(described["not_recomputed"])
    assert "not a forecast" in described["note"]


class NoDaily(FixtureProvider):
    def daily(self, cell_id):
        raise DataUnavailableError("sin serie diaria")


# ---------------------------------------------------------------- API


@pytest.fixture
def irrigated(client, headers):
    payload = field_payload(
        current_rotation=MAIZE_FALLOW,
        irrigation={"available": True, "source": "well", "max_mm_per_year": 400},
    )
    return client.post("/api/v1/fields", json=payload, headers=headers).json()


def test_suitability_with_a_scenario_reports_it(client, headers, irrigated):
    url = f"/api/v1/fields/{irrigated['id']}/suitability"
    params = {"crop_id": "maiz", "planting_month": 4, "delta_t_c": 2, "delta_p_pct": -20}
    response = client.get(url, params=params, headers=headers)
    assert response.status_code == 200
    scenario = response.json()["scenario"]
    assert (scenario["delta_t_c"], scenario["delta_p_pct"]) == (2, -20)
    assert scenario["daily_origin"] == "synthetic" and "pronóstico" in scenario["note"]


def test_zero_scenario_equals_no_scenario(client, headers, irrigated):
    url = f"/api/v1/fields/{irrigated['id']}/suitability"
    plain = client.get(url, params={"crop_id": "maiz", "planting_month": 4}, headers=headers)
    zero = client.get(
        url,
        params={"crop_id": "maiz", "planting_month": 4, "delta_t_c": 0, "delta_p_pct": 0},
        headers=headers,
    )
    assert plain.json() == zero.json()
    assert (
        client.get(url, headers=headers).json()
        == client.get(url, params={"delta_t_c": 0}, headers=headers).json()
    )


@pytest.mark.parametrize("params", [{"delta_t_c": 10}, {"delta_t_c": -3}, {"delta_p_pct": 60}])
def test_out_of_range_scenarios_are_422(client, headers, irrigated, params):
    response = client.get(
        f"/api/v1/fields/{irrigated['id']}/suitability", params=params, headers=headers
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    rotations = client.post(
        f"/api/v1/fields/{irrigated['id']}/rotations", json={"scenario": params}, headers=headers
    )
    assert rotations.status_code == 422


def test_a_warmer_scenario_hurts_maize_in_la_laguna_and_helps_frost(client, headers):
    laguna = field_payload(
        geometry={
            "type": "Polygon",
            "coordinates": [
                [
                    [-103.24, 25.55],
                    [-103.22, 25.55],
                    [-103.22, 25.57],
                    [-103.24, 25.57],
                    [-103.24, 25.55],
                ]
            ],
        }
    )
    field = client.post("/api/v1/fields", json=laguna, headers=headers).json()
    assert field["cell_id"] == LA_LAGUNA
    url = f"/api/v1/fields/{field['id']}/suitability"
    base = client.get(url, params={"crop_id": "maiz", "planting_month": 3}, headers=headers).json()
    warmer = client.get(
        url, params={"crop_id": "maiz", "planting_month": 3, "delta_t_c": 5}, headers=headers
    ).json()
    assert warmer["score"] <= base["score"]


def test_drier_scenario_never_lowers_the_irrigation_need(client, headers, irrigated):
    url = f"/api/v1/fields/{irrigated['id']}/rotations"
    base = client.post(url, json={"max_strategies": 6}, headers=headers).json()
    drier = client.post(
        url, json={"max_strategies": 6, "scenario": {"delta_p_pct": -20}}, headers=headers
    ).json()
    need = {s["id"]: s["metrics"]["irrigation_need_mm_per_year"] for s in base["strategies"]}
    for strategy in drier["strategies"]:
        if strategy["id"] in need:
            assert strategy["metrics"]["irrigation_need_mm_per_year"] >= need[strategy["id"]]
    assert drier["scenario"]["delta_p_pct"] == -20


def test_two_scenarios_in_a_row_answer_quickly(client, headers, irrigated):
    url = f"/api/v1/fields/{irrigated['id']}/suitability"
    client.get(url, params={"delta_t_c": 1}, headers=headers)
    started = time.perf_counter()
    response = client.get(url, params={"delta_t_c": 2}, headers=headers)
    assert response.status_code == 200 and time.perf_counter() - started < 2


def test_without_daily_series_only_scenarios_fail(settings, headers):
    client = TestClient(create_app(settings, data_provider=NoDaily()))
    field = client.post("/api/v1/fields", json=field_payload(), headers=headers).json()
    url = f"/api/v1/fields/{field['id']}/suitability"
    params = {"crop_id": "maiz", "planting_month": 4}
    failed = client.get(url, params={**params, "delta_t_c": 2}, headers=headers)
    assert failed.status_code == 503
    assert failed.json()["error"]["code"] == "daily_unavailable"
    assert client.get(url, params=params, headers=headers).status_code == 200
