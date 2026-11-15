import dataclasses
import re
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.schemas.profile import FieldProfile
from app.data.fixture import FixtureProvider
from app.main import create_app
from app.profile.builder import ProfileService, build_profile
from app.profile.gaps import GAP_SEVERITY, ProfileFacts, build_gaps
from app.profile.monthly import MonthlyIndicators, decade_start, month_day, percentile
from tests.helpers import field_payload, square

SALTILLO = "E9_r0463_c0846"
LA_LAGUNA = "E9_r0461_c0822"
DOCS = Path(__file__).resolve().parents[2] / "docs" / "api-contract.md"


@pytest.fixture(scope="module")
def provider():
    return FixtureProvider()


@pytest.fixture(scope="module")
def profile(provider):
    return build_profile(provider, SALTILLO, "es")


class EditedProvider(FixtureProvider):
    """Datos sintéticos con filas retocadas, para probar casos que no trae el generador."""

    def __init__(self, *, cell=None, indicators=None, climatology=None, soil=None, daily=None):
        super().__init__()
        self._edits = {
            "cell": cell,
            "indicators": indicators,
            "climatology": climatology,
            "soil": soil,
            "daily": daily,
        }

    def _edited(self, name, rows):
        edit = self._edits[name]
        return rows if edit is None else edit(rows)

    def cell(self, cell_id):
        return self._edited("cell", super().cell(cell_id))

    def indicators(self, cell_id):
        return self._edited("indicators", super().indicators(cell_id))

    def climatology(self, cell_id):
        return self._edited("climatology", super().climatology(cell_id))

    def soil(self, cell_id):
        return self._edited("soil", super().soil(cell_id))

    def daily(self, cell_id):
        return self._edited("daily", super().daily(cell_id))


def with_frost_in_march(rows, years_with_frost):
    """Sin heladas en marzo salvo en los años indicados, repartidas en varias decenas."""
    edited = []
    for row in rows:
        if row.month == 3:
            frost = 2 if row.year in years_with_frost and row.decade in (7, 8) else 0
            row = dataclasses.replace(row, frost_days=frost, frost_days_m2=0)
        edited.append(row)
    return edited


# ---------------------------------------------------------------- resumen mensual


def test_monthly_probability_is_the_share_of_years_with_an_event(provider):
    rows = with_frost_in_march(provider.indicators(SALTILLO), {2016, 2018, 2021, 2024})
    monthly = MonthlyIndicators(rows)
    # 4 de 10 años con helada, aunque cada uno la tuvo en dos decenas: no se suman.
    assert monthly.share_of_years_with(3, "frost_days") == 0.4
    assert monthly.mean_total(3, "frost_days") == pytest.approx(1.6)


def test_month_without_events_has_zero_probability(provider):
    monthly = MonthlyIndicators(with_frost_in_march(provider.indicators(SALTILLO), set()))
    assert monthly.share_of_years_with(3, "frost_days") == 0
    assert monthly.mean_total(3, "frost_days") == 0


def test_profile_reports_the_monthly_frost_probability(provider):
    edited = EditedProvider(
        indicators=lambda rows: with_frost_in_march(rows, {2016, 2018, 2021, 2024})
    )
    march = build_profile(edited, SALTILLO, "es")["climate"]["frost"]["by_month"][2]
    assert march["month"] == 3 and march["prob_any_frost"] == 0.4


def test_saltillo_is_frostier_in_january_than_in_july(profile):
    frost = profile["climate"]["frost"]
    by_month = {entry["month"]: entry for entry in frost["by_month"]}
    assert by_month[1]["prob_any_frost"] > by_month[7]["prob_any_frost"] == 0
    assert by_month[1]["record_tmin_c"] < 0
    assert frost["threshold_c"] == 0 and frost["severe_threshold_c"] == -2
    assert frost["years_analyzed"] == 10
    assert frost["last_spring_frost"]["p50"]["date"] < "04-01"
    assert frost["first_fall_frost"]["p50"]["date"] > "10-15"


def test_climate_sections_carry_thresholds_units_and_years(profile):
    climate = profile["climate"]
    assert climate["source_id"] == "nasa_power" and climate["years"] == [2016, 2025]
    assert climate["heat"]["thresholds_c"] == [30, 32, 35, 38]
    assert climate["rain"]["heavy_rain_threshold_mm"] == 25
    assert climate["rain"]["annual_p20_mm"] <= climate["rain"]["annual_mean_mm"]
    assert set(climate["rain"]["rainy_months"]) <= {5, 6, 7, 8, 9, 10}
    wind = climate["wind"]
    # km/h: el viento máximo anual sintético ronda los 12-15 m/s.
    assert 35 < wind["annual_max_mean_kmh"] <= wind["record_kmh"] < 80
    assert [level["return_period_years"] for level in wind["return_levels_kmh"]] == [10, 25, 50]


def test_helpers_for_dates_and_percentiles():
    assert [decade_start(decade) for decade in (1, 2, 3, 36)] == [
        "01-01",
        "01-11",
        "01-21",
        "12-21",
    ]
    assert [month_day(day) for day in (1, 59, 60, 365)] == ["01-01", "02-28", "03-01", "12-31"]
    assert percentile([1, 2, 3, 4, 5], 50) == 3
    assert percentile([None], 50) is None


# ---------------------------------------------------------------- calendario


def test_risk_calendar_has_36_decades_with_their_start(profile):
    calendar = profile["climate"]["risk_calendar"]
    assert [entry["decade"] for entry in calendar] == list(range(1, 37))
    assert calendar[4]["starts"] == "02-11" and calendar[4]["month"] == 2
    for column in ("p_frost", "p_frost_severe", "p_heat_30c", "p_heat_38c", "p_heavy_rain"):
        assert all(0 <= entry[column] <= 1 for entry in calendar)


def test_vulnerable_decade_keeps_its_reasons(provider, profile):
    source = {row.decade: row for row in provider.climatology(SALTILLO)}
    flagged = [entry for entry in profile["climate"]["risk_calendar"] if entry["vulnerable"]]
    assert flagged
    for entry in flagged:
        assert entry["vulnerable_reasons"] == source[entry["decade"]].vulnerable_reasons.split(",")
    assert any("frost" in entry["vulnerable_reasons"] for entry in flagged)
    calm = next(e for e in profile["climate"]["risk_calendar"] if not e["vulnerable"])
    assert calm["vulnerable_reasons"] == []


# ---------------------------------------------------------------- suelo, agua, vegetación


def test_soil_has_three_depths_with_their_uncertainty(profile):
    soil = profile["soil"]
    assert soil["source_id"] == "soilgrids" and soil["confidence"] == "medium"
    assert soil["lab"] is None
    assert [layer["depth_cm"] for layer in soil["layers"]] == [[0, 5], [5, 15], [15, 30]]
    top = soil["layers"][0]
    assert top["uncertainty"]["ph"]["p05"] < top["ph"] < top["uncertainty"]["ph"]["p95"]
    assert top["om_pct"] == pytest.approx(top["soc_g_kg"] * 1.724 / 10, abs=0.05)


def test_profile_without_soil_declares_the_gap():
    profile = build_profile(EditedProvider(soil=lambda rows: ()), SALTILLO, "es")
    assert profile["soil"] is None
    assert "no_soil_data" in {gap["code"] for gap in profile["gaps"]}
    assert "soilgrids" not in {source["id"] for source in profile["sources"]}


def test_water_uses_the_moisture_source_actually_used(profile):
    water = profile["water"]
    assert water["groundwater"] is None
    assert water["soil_moisture"]["source_id"] == "nasa_power"
    months = water["soil_moisture"]["by_month"]
    assert all(m["percentile_p10"] <= m["percentile_p50"] <= m["percentile_p90"] for m in months)
    assert water["et"]["method"].startswith("Hargreaves")
    balance = {entry["month"]: entry["p_minus_et0_mm"] for entry in water["water_balance_by_month"]}
    assert balance[5] < 0


def test_smap_moisture_removes_the_model_gap():
    edited = EditedProvider(
        indicators=lambda rows: [dataclasses.replace(row, sm_src="smap_l4") for row in rows]
    )
    profile = build_profile(edited, SALTILLO, "es")
    assert profile["water"]["soil_moisture"]["source_id"] == "smap_l4"
    assert "soil_moisture_from_model" not in {gap["code"] for gap in profile["gaps"]}
    assert "smap_l4" in {source["id"] for source in profile["sources"]}


def test_vegetation_is_null_without_ndvi(profile):
    assert profile["vegetation"] is None
    assert "ndvi_not_available" in {gap["code"] for gap in profile["gaps"]}


def test_vegetation_reports_ndvi_and_bare_soil_when_published():
    edited = EditedProvider(
        indicators=lambda rows: [
            dataclasses.replace(row, ndvi_mean=0.2 if row.month <= 3 else 0.5) for row in rows
        ],
        climatology=lambda rows: [
            dataclasses.replace(row, bare_prob=0.8 if row.decade <= 8 else 0.1) for row in rows
        ],
    )
    profile = build_profile(edited, SALTILLO, "es")
    vegetation = profile["vegetation"]
    assert vegetation["source_id"] == "modis_ndvi"
    assert vegetation["ndvi_by_month"][0]["mean"] == 0.2
    assert vegetation["bare_soil_decades"] == list(range(1, 9))
    # Marzo solo tiene dos de sus tres decenas descubiertas: sigue contando.
    assert vegetation["bare_soil_months"] == [1, 2, 3]
    assert "ndvi_not_available" not in {gap["code"] for gap in profile["gaps"]}
    assert profile["climate"]["risk_calendar"][0]["p_bare_soil"] == 0.8


# ---------------------------------------------------------------- vacíos y procedencia


def facts(provider, **changes):
    values = {
        "cell": provider.cell(SALTILLO),
        "synthetic": False,
        "soil_moisture_source": "smap_l4",
        "has_soil": True,
        "has_vegetation": True,
        "has_wind": True,
        "has_daily": True,
    }
    values.update(changes)
    return ProfileFacts(**values)


def codes(gaps):
    return {gap["code"] for gap in gaps}


PERMANENT = {
    "zonal_resolution_9km",
    "no_lab_analysis",
    "shared_climate_series",
    "no_slope_data",
    "no_groundwater_source",
    "no_light_data",
    "no_land_use_history",
    "no_hail_product",
}


def test_permanent_gaps_are_always_declared(provider):
    assert codes(build_gaps(facts(provider), "es")) == PERMANENT


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"synthetic": True}, "synthetic_data"),
        ({"soil_moisture_source": "nasa_power"}, "soil_moisture_from_model"),
        ({"soil_moisture_source": None}, "soil_moisture_from_model"),
        ({"has_vegetation": False}, "ndvi_not_available"),
        ({"has_soil": False}, "no_soil_data"),
        ({"has_wind": False}, "no_wind_data"),
        ({"has_daily": False}, "no_daily_series"),
    ],
)
def test_each_rule_adds_its_gap(provider, changes, code):
    assert codes(build_gaps(facts(provider, **changes), "es")) == PERMANENT | {code}


def test_mountain_cell_declares_the_elevation_mismatch(provider):
    cell = provider.cell(SALTILLO)
    sierra = dataclasses.replace(cell, cell_elev_m=cell.power_elev_m + 450)
    gaps = build_gaps(facts(provider, cell=sierra), "es")
    gap = next(gap for gap in gaps if gap["code"] == "elevation_mismatch")
    assert gap["severity"] == "medium"
    assert "450 m" in gap["message"] and "estimación corregida por altura" in gap["message"]
    close = dataclasses.replace(cell, cell_elev_m=cell.power_elev_m + 300)
    assert "elevation_mismatch" not in codes(build_gaps(facts(provider, cell=close), "es"))


def test_cell_without_elevation_and_unshared_climate(provider):
    cell = dataclasses.replace(
        provider.cell(SALTILLO), cell_elev_m=None, climate_shared_by_n_cells=1
    )
    gaps = codes(build_gaps(facts(provider, cell=cell), "es"))
    assert "no_elevation_data" in gaps and "shared_climate_series" not in gaps
    profile = build_profile(EditedProvider(cell=lambda _: cell), SALTILLO, "es")
    assert profile["terrain"] is None and profile["climate"]["elevation_m"] is None


def test_every_gap_code_has_a_severity_and_both_languages(provider):
    everything = facts(
        provider,
        cell=dataclasses.replace(provider.cell(SALTILLO), cell_elev_m=10.0),
        synthetic=True,
        soil_moisture_source=None,
        has_soil=False,
        has_vegetation=False,
        has_wind=False,
        has_daily=False,
    )
    spanish, english = build_gaps(everything, "es"), build_gaps(everything, "en")
    without_elevation = build_gaps(
        facts(provider, cell=dataclasses.replace(provider.cell(SALTILLO), cell_elev_m=None)), "es"
    )
    assert codes(spanish) | codes(without_elevation) == set(GAP_SEVERITY)
    for es, en in zip(spanish, english, strict=True):
        assert es["severity"] == en["severity"] in {"low", "medium", "high"}
        assert es["message"] and en["message"] and es["message"] != en["message"]


def source_ids(node):
    if isinstance(node, dict):
        if isinstance(node.get("source_id"), str):
            yield node["source_id"]
        for value in node.values():
            yield from source_ids(value)
    elif isinstance(node, list):
        for value in node:
            yield from source_ids(value)


@pytest.mark.parametrize("cell_id", [SALTILLO, LA_LAGUNA])
def test_sources_are_exactly_the_referenced_ones(provider, cell_id):
    profile = build_profile(provider, cell_id, "es")
    body = {key: value for key, value in profile.items() if key != "sources"}
    listed = [source["id"] for source in profile["sources"]]
    assert sorted(listed) == sorted(set(source_ids(body)))
    assert len(listed) == len(set(listed))
    for source in profile["sources"]:
        assert source["resolution"] and source["period"] and source["data_class"]


def texts(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in {"message", "note"} and isinstance(value, str):
                yield value
            yield from texts(value)
    elif isinstance(node, list):
        for value in node:
            yield from texts(value)


PLOT_CLAIMS = re.compile(
    r"tu parcela tiene|tu terreno tiene|en tu parcela|your field has|your plot has|on your plot",
    re.IGNORECASE,
)


@pytest.mark.parametrize("language", ["es", "en"])
def test_texts_speak_about_the_zone_never_the_plot(provider, language):
    everything = EditedProvider(
        cell=lambda cell: dataclasses.replace(cell, cell_elev_m=cell.power_elev_m + 450),
        soil=lambda rows: (),
    )
    messages = list(texts(build_profile(everything, SALTILLO, language)))
    assert len(messages) >= 10
    assert [message for message in messages if PLOT_CLAIMS.search(message)] == []
    zonal = "celda de 9 km" if language == "es" else "9 km cell"
    assert zonal in messages[0]


# ---------------------------------------------------------------- endpoint


def test_profile_endpoint_returns_the_profile_of_the_field_cell(client, headers, field):
    response = client.get(f"/api/v1/fields/{field['id']}/profile", headers=headers)
    assert response.status_code == 200
    assert "x-fieldshift-mock" not in response.headers
    profile = FieldProfile.model_validate(response.json())
    assert profile.status == "ready" and profile.field_id == field["id"]
    assert profile.cell_id == field["cell_id"] == SALTILLO
    assert profile.zone_id == field["zone_id"]
    assert profile.data_version == "fixture" and profile.computed_at.year >= 2026


def test_profile_of_a_foreign_or_missing_field_is_404(client, headers, field):
    other = {"X-Client-Id": "3f0f6a1e-8f0a-4b55-9d59-1c2f0f1a2b3c"}
    assert client.get(f"/api/v1/fields/{field['id']}/profile", headers=other).status_code == 404
    missing = "/api/v1/fields/fld_01KA0Z5T9M3X8Q2W4E6R7T8Y9A/profile"
    assert client.get(missing, headers=headers).status_code == 404


def test_profile_follows_the_request_language(client, headers, field):
    url = f"/api/v1/fields/{field['id']}/profile"
    spanish = client.get(url, headers=headers).json()
    english = client.get(url, headers={**headers, "Accept-Language": "en"}).json()
    assert "celda de 9 km" in spanish["gaps"][0]["message"]
    assert "9 km cell" in english["gaps"][0]["message"]
    assert spanish["climate"] == english["climate"]


def test_field_in_a_cell_without_data_is_503(client, headers):
    # Zona piloto, pero fuera de las dos celdas con datos sintéticos.
    payload = field_payload(geometry=square(-101.3, 25.3))
    created = client.post("/api/v1/fields", json=payload, headers=headers)
    assert created.status_code == 201 and created.json()["cell_id"] != SALTILLO
    response = client.get(f"/api/v1/fields/{created.json()['id']}/profile", headers=headers)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "data_unavailable"


def test_second_call_is_served_from_memory(settings, headers):
    client = TestClient(create_app(settings))
    field = client.post("/api/v1/fields", json=field_payload(), headers=headers).json()
    url = f"/api/v1/fields/{field['id']}/profile"
    first = client.get(url, headers=headers).json()
    started = time.perf_counter()
    second = client.get(url, headers=headers).json()
    assert time.perf_counter() - started < 0.2
    assert second["computed_at"] == first["computed_at"]


def test_cache_is_keyed_by_cell_version_and_language(provider):
    service = ProfileService(provider)
    spanish = service.for_cell(SALTILLO, "es")
    assert service.for_cell(SALTILLO, "es") is spanish
    assert service.for_cell(SALTILLO, "en") is not spanish
    assert service.for_cell(LA_LAGUNA, "es")["cell_id"] == LA_LAGUNA


def test_documented_gap_codes_exist(provider):
    documented = set(
        re.findall(r"^\| `([a-z0-9_]+)` \| (?:low|medium|high) \|", DOCS.read_text("utf-8"), re.M)
    )
    assert documented == set(GAP_SEVERITY)
