import copy
import dataclasses
import re
import time
from pathlib import Path

import pytest
import yaml

from app.api.schemas.suitability import SuitabilityDetail, SuitabilityMatrix
from app.catalog.loader import load_catalog
from app.catalog.models import Crop
from app.config import Settings
from app.data.fixture import FixtureProvider
from app.engines import config as engine_config
from app.engines.config import EngineConfigError, load_config, parse_config
from app.engines.suitability import (
    CellData,
    FieldContext,
    cycle_days,
    evaluate,
    evaluate_matrix,
    flowering_decades,
    harvest_window,
    nearest_heat_threshold,
    occupied_decades,
)
from app.engines.water import stage_coefficients, water_balance
from app.main import create_app
from tests.helpers import field_payload

SALTILLO = "E9_r0463_c0846"
LA_LAGUNA = "E9_r0461_c0822"
DOCS = Path(__file__).resolve().parents[2] / "docs" / "engines.md"
IRRIGATED = FieldContext(irrigation_declared=True, irrigation_mm=None)


@pytest.fixture(scope="module")
def provider():
    return FixtureProvider()


@pytest.fixture(scope="module")
def catalog():
    return load_catalog()


@pytest.fixture(scope="module")
def config():
    return load_config().suitability


def cell(provider, cell_id=SALTILLO, **climate) -> CellData:
    rows = provider.climatology(cell_id)
    if climate:
        rows = [dataclasses.replace(row, **climate) for row in rows]
    return CellData(climatology=rows, soil=provider.soil(cell_id))


def crop_with(catalog, crop_id="maiz", **values) -> Crop:
    return Crop.model_validate({**catalog.get(crop_id).model_dump(), **values})


# ---------------------------------------------------------------- configuración


def test_shipped_config_loads(config):
    assert config.status_cuts.suitable == 70 and config.status_cuts.marginal == 40
    assert config.water.effective_rain_fraction == 0.8
    assert config.heat.flowering_window == (0.55, 0.65)
    assert sum(config.weights.values()) == pytest.approx(1)


@pytest.mark.parametrize(
    ("path", "value", "named"),
    [
        (("status_cuts", "suitable"), 140, "status_cuts.suitable"),
        (("status_cuts", "marginal"), 80, "marginal debe ser menor"),
        (("weights", "frost"), 0.9, "weights debe sumar 1"),
        (("frost", "warn_prob"), 0.8, "warn_prob debe ser menor"),
        (("water", "effective_rain_fraction"), 1.5, "effective_rain_fraction"),
        (("water", "stage_fractions", "ini"), 0.6, "deben sumar 1"),
        (("heat", "flowering_window"), [0.7, 0.6], "flowering_window"),
        (("exclusive_score_cap",), 55, "exclusive_score_cap"),
        (("exclusive_factors",), ["hail"], "exclusive_factors"),
        (("unknown_parameter",), 1, "unknown_parameter"),
    ],
)
def test_out_of_range_parameters_are_rejected_by_name(path, value, named):
    document = yaml.safe_load(engine_config.DEFAULT_PATH.read_text(encoding="utf-8"))
    node = document["suitability"]
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    with pytest.raises(EngineConfigError, match=named):
        parse_config(document)


def test_app_does_not_start_with_an_invalid_engine_config(monkeypatch, tmp_path):
    path = tmp_path / "engine.yaml"
    path.write_text("suitability: {}", encoding="utf-8")
    monkeypatch.setattr("app.main.load_config", lambda: load_config(path))
    with pytest.raises(EngineConfigError):
        create_app(Settings())
    with pytest.raises(EngineConfigError):
        load_config(tmp_path / "missing.yaml")


# ---------------------------------------------------------------- calendario


def test_cycle_of_120_days_from_april_occupies_twelve_decades():
    assert occupied_decades(4, 120) == list(range(10, 22))


def test_cycle_crossing_december_wraps_to_january():
    assert occupied_decades(11, 120) == [31, 32, 33, 34, 35, 36, 1, 2, 3, 4, 5, 6]


def test_harvest_window_uses_the_shortest_and_longest_cycle(catalog):
    maize = catalog.get("maiz")  # 100-150 días
    assert cycle_days(maize) == 125
    assert harvest_window(4, maize) == ("07-10", "08-29")
    assert harvest_window(11, maize) == ("02-09", "03-31")


def test_flowering_window_is_the_55_to_65_percent_of_the_cycle():
    assert flowering_decades(list(range(10, 22)), (0.55, 0.65)) == [16, 17]
    assert flowering_decades([1, 2, 3], (0.55, 0.65)) == [2]


@pytest.mark.parametrize(
    ("critical", "threshold"), [(34, 35), (35, 35), (31, 30), (30.9, 30), (33.5, 32), (45, 38)]
)
def test_heat_uses_the_nearest_published_threshold(critical, threshold):
    assert nearest_heat_threshold(critical) == threshold


# ---------------------------------------------------------------- factores


def test_first_commit_signature_is_stable(provider, catalog, config):
    evaluation = evaluate(
        catalog.get("maiz"), 4, cell(provider), FieldContext(), None, config=config
    )
    assert [reason.factor for reason in evaluation.reasons] == ["frost", "heat", "water", "soil"]
    assert 0 <= evaluation.score <= 100


def test_maize_in_january_is_excluded_by_frost_in_saltillo(provider, catalog, config):
    evaluation = evaluate(catalog.get("maiz"), 1, cell(provider), IRRIGATED, config=config)
    frost = evaluation.reason("frost")
    assert frost.status == "bad" and frost.source_id == "nasa_power"
    assert evaluation.status == "unsuitable" and evaluation.score <= 39
    assert "no tolera heladas" in frost.detail and "0 °C" in frost.detail


def test_frost_tolerant_oat_in_november_is_not_bad(provider, catalog, config):
    evaluation = evaluate(
        catalog.get("avena_forrajera"), 11, cell(provider), IRRIGATED, config=config
    )
    frost = evaluation.reason("frost")
    assert frost.status != "bad"
    assert "tolera heladas ligeras" in frost.detail and "-2 °C" in frost.detail
    assert evaluation.status != "unsuitable"


def test_tolerant_crop_is_never_excluded_even_with_hard_frost(provider, catalog, config):
    harsh = cell(provider, frost_m2_prob=0.9)
    frost = evaluate(catalog.get("veza"), 11, harsh, IRRIGATED, config=config).reason("frost")
    assert frost.status == "warn" and "90 %" in frost.detail


def test_heat_detail_names_the_threshold_used(provider, catalog, config):
    crop = crop_with(catalog, heat_critical_c=34)
    heat = evaluate(crop, 4, cell(provider), IRRIGATED, config=config).reason("heat")
    assert "umbral usado: 35 °C" in heat.detail and "34 °C" in heat.detail


def test_la_laguna_summer_heat_damages_maize_flowering(provider, catalog, config):
    laguna = evaluate(catalog.get("maiz"), 4, cell(provider, LA_LAGUNA), IRRIGATED, config=config)
    saltillo = evaluate(catalog.get("maiz"), 4, cell(provider), IRRIGATED, config=config)
    assert laguna.reason("heat").status == "bad"
    assert laguna.reason("heat").score < saltillo.reason("heat").score
    winter = evaluate(catalog.get("maiz"), 10, cell(provider, LA_LAGUNA), IRRIGATED, config=config)
    assert winter.reason("heat").status == "ok"


def flat_climate(provider, et0, rain):
    """Clima sin heladas ni calor, con ET0 y lluvia iguales en todas las decenas."""
    return cell(
        provider,
        frost_prob=0.0,
        frost_m2_prob=0.0,
        hot_prob_30=0.0,
        hot_prob_32=0.0,
        hot_prob_35=0.0,
        hot_prob_38=0.0,
        et0_p50=et0,
        precip_p50=rain,
    )


def test_water_deficit_of_620_240_and_200_mm(provider, catalog, config):
    # 12 decenas con Kc 1: demanda 620 mm; lluvia 300 mm × 0.8 = 240 mm efectivos.
    crop = crop_with(catalog, cycle_days=[120, 120], kc={"ini": 1, "mid": 1, "end": 1})
    data = flat_climate(provider, et0=620 / 12, rain=300 / 12)
    context = FieldContext(irrigation_declared=True, irrigation_mm=200)
    evaluation = evaluate(crop, 4, data, context, config=config)
    assert evaluation.water.demand_mm == pytest.approx(620)
    assert evaluation.water.effective_rain_mm == pytest.approx(240)
    assert evaluation.water.deficit_mm == pytest.approx(180)
    water = evaluation.reason("water")
    assert water.status == "bad"
    assert all(value in water.detail for value in ("620 mm", "240 mm", "200 mm", "180 mm"))


def test_field_without_declared_irrigation_is_evaluated_as_rainfed(provider, catalog, config):
    crop = crop_with(catalog, cycle_days=[120, 120], kc={"ini": 1, "mid": 1, "end": 1})
    data = flat_climate(provider, et0=620 / 12, rain=300 / 12)
    water = evaluate(crop, 4, data, FieldContext(), config=config).reason("water")
    assert water.status == "bad"
    assert "temporal" in water.detail and "380 mm" in water.detail


def test_irrigation_levels_change_the_water_factor(provider, catalog, config):
    crop = crop_with(catalog, cycle_days=[120, 120], kc={"ini": 1, "mid": 1, "end": 1})
    data = flat_climate(provider, et0=620 / 12, rain=300 / 12)

    def status(mm):
        context = FieldContext(irrigation_declared=True, irrigation_mm=mm)
        return evaluate(crop, 4, data, context, config=config).reason("water").status

    assert [status(380), status(300), status(0)] == ["ok", "warn", "bad"]
    unlimited = evaluate(crop, 4, data, IRRIGATED, config=config).reason("water")
    assert unlimited.status == "ok" and "sin indicar cuánto" in unlimited.detail


def test_kc_follows_the_crop_stages(catalog, config):
    maize = catalog.get("maiz")
    coefficients = stage_coefficients(maize, 10, config.water)
    assert coefficients == [0.3] * 2 + [1.2] * 5 + [0.6] * 3


def test_water_balance_is_unknown_without_et0(provider, catalog, config):
    data = cell(provider, et0_p50=None)
    assert water_balance(catalog.get("maiz"), data.climatology[:12], 0.0, config.water) is None
    evaluation = evaluate(catalog.get("maiz"), 4, data, FieldContext(), config=config)
    assert evaluation.reason("water").status == "unknown" and evaluation.confidence == "low"


def soil_with(provider, **values):
    return [dataclasses.replace(layer, **values) for layer in provider.soil(SALTILLO)]


def test_ph_outside_the_crop_range_is_reported_with_both_values(provider, catalog, config):
    data = CellData(provider.climatology(SALTILLO), soil_with(provider, ph=8.4))
    soil = evaluate(catalog.get("maiz"), 4, data, IRRIGATED, config=config).reason("soil")
    assert soil.status in {"warn", "bad"} and soil.source_id == "soilgrids"
    assert "8.4" in soil.detail and "5.5-7.5" in soil.detail


@pytest.mark.parametrize(
    ("ph", "texture", "status"),
    [
        (6.5, "loam", "ok"),
        (7.8, "loam", "warn"),
        (8.4, "loam", "bad"),
        (6.5, "clay", "warn"),
        (5.1, "loam", "warn"),
    ],
)
def test_soil_factor_levels(provider, catalog, config, ph, texture, status):
    data = CellData(
        provider.climatology(SALTILLO), soil_with(provider, ph=ph, texture_class=texture)
    )
    soil = evaluate(catalog.get("maiz"), 4, data, IRRIGATED, config=config).reason("soil")
    assert soil.status == status
    assert ("textura" in soil.detail) == (texture == "clay")


def test_missing_soil_is_unknown_and_lowers_confidence(provider, catalog, config):
    data = CellData(provider.climatology(SALTILLO), soil=())
    evaluation = evaluate(catalog.get("sorgo"), 5, data, IRRIGATED, config=config)
    soil = evaluation.reason("soil")
    assert soil.status == "unknown" and soil.source_id is None and soil.score is None
    assert evaluation.confidence == "low"
    with_soil = evaluate(catalog.get("sorgo"), 5, cell(provider), IRRIGATED, config=config)
    assert with_soil.confidence == "medium"
    assert 0 < evaluation.score <= 100


# ---------------------------------------------------------------- puntaje


def test_the_three_states_are_reachable(provider, catalog, config):
    crop = crop_with(catalog, cycle_days=[120, 120], kc={"ini": 1, "mid": 1, "end": 1})
    data = flat_climate(provider, et0=50, rain=25)
    good_soil = CellData(data.climatology, soil_with(provider, ph=6.5, texture_class="loam"))

    def state(mm):
        context = FieldContext(irrigation_declared=True, irrigation_mm=mm)
        return evaluate(crop, 4, good_soil, context, config=config)

    assert state(None).status == "suitable" and state(None).score == 100
    # Sin riego y con un pH muy alto, agua y suelo bajan el puntaje a marginal.
    poor_soil = CellData(data.climatology, soil_with(provider, ph=8.6))
    rainfed = evaluate(crop, 4, poor_soil, FieldContext(), config=config)
    assert rainfed.status == "marginal"
    frozen = CellData(
        [dataclasses.replace(row, frost_prob=0.9) for row in good_soil.climatology], good_soil.soil
    )
    assert state(None).score > evaluate(crop, 4, frozen, IRRIGATED, config=config).score
    assert evaluate(crop, 4, frozen, IRRIGATED, config=config).status == "unsuitable"


def test_exclusive_factor_caps_the_score_below_marginal(provider, catalog, config):
    data = flat_climate(provider, et0=10, rain=40)
    frozen = CellData(
        [dataclasses.replace(row, frost_prob=0.6) for row in data.climatology],
        soil_with(provider, ph=6.5, texture_class="loam"),
    )
    evaluation = evaluate(catalog.get("maiz"), 4, frozen, IRRIGATED, config=config)
    # Calor, agua y suelo perfectos: sin el tope, el puntaje superaría el corte.
    assert [r.status for r in evaluation.reasons] == ["bad", "ok", "ok", "ok"]
    assert evaluation.score == config.exclusive_score_cap < config.status_cuts.marginal


def test_same_input_gives_the_same_output(provider, catalog, config):
    first = evaluate(catalog.get("frijol"), 6, cell(provider), FieldContext(), config=config)
    second = evaluate(catalog.get("frijol"), 6, cell(provider), FieldContext(), config=config)
    assert first == second and first.reasons == second.reasons


@pytest.mark.parametrize("language", ["es", "en"])
def test_details_carry_values_and_never_claim_plot_facts(provider, catalog, config, language):
    context = FieldContext(irrigation_declared=True, irrigation_mm=150, language=language)
    for crop in catalog:
        for month in (1, 4, 7, 10):
            for reason in evaluate(crop, month, cell(provider), context, config=config).reasons:
                assert re.search(r"\d", reason.detail), reason.detail
                assert not re.search(r"tu parcela|your plot|your field", reason.detail, re.I)
                assert "{" not in reason.detail
    english = evaluate(catalog.get("maiz"), 1, cell(provider), context, config=config)
    assert ("your zone" in english.reason("frost").detail) == (language == "en")


def test_matrix_is_fast_with_fifteen_crops(provider, catalog, config):
    crops = [
        crop_with(catalog, crop.id, id=f"{crop.id}_{copy_n}")
        for copy_n in range(3)
        for crop in catalog
    ]
    assert len(crops) == 15
    started = time.perf_counter()
    matrix = evaluate_matrix(crops, cell(provider), FieldContext(), config=config)
    assert time.perf_counter() - started < 0.3
    assert all(len(evaluations) == 12 for evaluations in matrix.values())


# ---------------------------------------------------------------- endpoint


@pytest.fixture
def irrigated_field(client, headers):
    payload = field_payload(
        irrigation={"available": True, "source": "well", "max_mm_per_year": 400}
    )
    return client.post("/api/v1/fields", json=payload, headers=headers).json()


def test_detail_endpoint_explains_the_four_factors(client, headers, irrigated_field):
    url = f"/api/v1/fields/{irrigated_field['id']}/suitability"
    response = client.get(url, params={"crop_id": "maiz", "planting_month": 4}, headers=headers)
    assert response.status_code == 200 and "x-fieldshift-mock" not in response.headers
    detail = SuitabilityDetail.model_validate(response.json())
    assert 0 <= detail.score <= 100
    assert [reason.factor for reason in detail.reasons] == ["frost", "heat", "water", "soil"]
    assert all(reason.detail and reason.source_id for reason in detail.reasons)
    assert response.json()["harvest_window"] == {"from": "07-10", "to": "08-29"}
    assert "400 mm de riego" in response.json()["reasons"][2]["detail"]
    sources = {source["id"] for source in client.get("/api/v1/sources").json()}
    assert {reason.source_id for reason in detail.reasons} <= sources


def test_detail_follows_the_language_and_the_declared_irrigation(client, headers, field):
    url = f"/api/v1/fields/{field['id']}/suitability"
    params = {"crop_id": "maiz", "planting_month": 4}
    spanish = client.get(url, params=params, headers=headers).json()
    english = client.get(url, params=params, headers={**headers, "Accept-Language": "en"}).json()
    assert "temporal" in spanish["reasons"][2]["detail"]
    assert "rainfed" in english["reasons"][2]["detail"]
    assert spanish["score"] == english["score"]


def test_unknown_crop_is_404_and_invalid_month_is_422(client, headers, field):
    url = f"/api/v1/fields/{field['id']}/suitability"
    unknown = client.get(url, params={"crop_id": "kiwi", "planting_month": 4}, headers=headers)
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "crop_not_found"
    assert unknown.json()["error"]["details"] == {"crop_id": "kiwi"}
    invalid = client.get(url, params={"crop_id": "maiz", "planting_month": 13}, headers=headers)
    assert invalid.status_code == 422


def test_matrix_matches_the_individual_evaluations(client, headers, irrigated_field):
    url = f"/api/v1/fields/{irrigated_field['id']}/suitability"
    response = client.get(url, headers=headers)
    assert response.status_code == 200
    matrix = SuitabilityMatrix.model_validate(response.json())
    assert matrix.months == list(range(1, 13))
    assert [row.crop_id for row in matrix.crops] == [crop.id for crop in load_catalog()]
    for row in matrix.crops:
        for month in (1, 6, 11):
            params = {"crop_id": row.crop_id, "planting_month": month}
            detail = client.get(url, params=params, headers=headers).json()
            assert detail["score"] == row.scores[month - 1]
            assert detail["status"] == row.status[month - 1]
    assert client.get(url, headers=headers).json() == response.json()


def test_field_in_a_cell_without_data_is_503(client, headers):
    from tests.helpers import square

    created = client.post(
        "/api/v1/fields", json=field_payload(geometry=square(-101.3, 25.3)), headers=headers
    )
    response = client.get(f"/api/v1/fields/{created.json()['id']}/suitability", headers=headers)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "data_unavailable"


# ---------------------------------------------------------------- documentación


def _leaves(node, prefix=""):
    for key, value in node.items():
        if isinstance(value, dict):
            yield from _leaves(value, f"{prefix}{key}.")
        else:
            yield f"{prefix}{key}"


def test_every_parameter_is_documented():
    document = yaml.safe_load(engine_config.DEFAULT_PATH.read_text(encoding="utf-8"))
    text = DOCS.read_text(encoding="utf-8")
    missing = [name for name in _leaves(copy.deepcopy(document)) if f"`{name}`" not in text]
    assert missing == []
