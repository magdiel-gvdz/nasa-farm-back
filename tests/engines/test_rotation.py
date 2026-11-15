import dataclasses
import re
import time
from pathlib import Path

import pytest

from app.api.routes.suitability import cell_data
from app.api.schemas.rotations import RotationResponse, StrategyMetrics
from app.catalog.loader import Catalog, load_catalog
from app.catalog.models import Crop
from app.data.fixture import FixtureProvider
from app.engines.config import EngineConfigError, load_config, parse_config
from app.engines.rotation import Constraints, CurrentRotationRequiredError, compare
from app.engines.rotation.candidates import ANY_STATUS, STRICT, Planner, UnknownCropError
from app.engines.rotation.explain import rule_keys
from app.engines.rotation.score import PRIORITIES, score
from app.engines.rotation.simulate import pest_break_score, simulate
from app.engines.suitability import CellData, FieldContext
from app.i18n import MESSAGES
from tests.helpers import MAIZE_FALLOW, field_payload

SALTILLO = "E9_r0463_c0846"
LA_LAGUNA = "E9_r0461_c0822"
DOCS = Path(__file__).resolve().parents[2] / "docs" / "engines.md"
EQUAL = dict.fromkeys(PRIORITIES, 3)
MAIZE_BEAN = [
    {"year": 1, "season": "spring_summer", "crop_id": "maiz"},
    {"year": 1, "season": "fall_winter", "crop_id": None},
    {"year": 2, "season": "spring_summer", "crop_id": "frijol"},
    {"year": 2, "season": "fall_winter", "crop_id": None},
]


@pytest.fixture(scope="module")
def provider():
    return FixtureProvider()


@pytest.fixture(scope="module")
def catalog():
    return load_catalog()


@pytest.fixture(scope="module")
def config():
    return load_config()


def run(provider, catalog, config, rotation=MAIZE_FALLOW, cell=SALTILLO, **options):
    arguments = {
        "catalog": catalog,
        "cell_data": cell_data(provider, cell),
        "field_context": FieldContext(irrigation_declared=True, irrigation_mm=None),
        "config": config,
        "current_rotation": rotation,
        "constraints": Constraints(),
        "weights": EQUAL,
        "irrigation_limit_mm": None,
    }
    arguments.update(options)
    return compare(**arguments)


def by_id(result):
    return {strategy["id"]: strategy for strategy in result["strategies"]}


def crops_of(strategy):
    return [step["crop_id"] for step in strategy["sequence"]]


def planner(provider, catalog, config, constraints=None, cell=SALTILLO):
    context = FieldContext(irrigation_declared=True, irrigation_mm=None)
    return Planner(
        catalog, cell_data(provider, cell), context, config, constraints or Constraints()
    )


# ---------------------------------------------------------------- candidatos


def test_one_year_rotation_is_normalized_with_its_fallow(provider, catalog, config):
    current = planner(provider, catalog, config).current(
        [{"year": 1, "season": "spring_summer", "crop_id": "maiz"}]
    )
    assert current.is_current and current.years == 1 and current.main.id == "maiz"
    assert [(s.year, s.season, s.crop.id if s.crop else None) for s in current.slots] == [
        (1, "spring_summer", "maiz"),
        (1, "fall_winter", None),
    ]
    assert current.slots[0].planting_month == 5 and current.slots[1].role == "bare"


def test_two_year_rotation_keeps_years_and_seasons_in_order(provider, catalog, config):
    declared = [
        {"year": 3, "season": "fall_winter", "crop_id": "avena_forrajera"},
        {"year": 2, "season": "spring_summer", "crop_id": "maiz"},
    ]
    current = planner(provider, catalog, config).current(declared)
    assert [(s.year, s.season, s.crop.id if s.crop else None) for s in current.slots] == [
        (1, "spring_summer", "maiz"),
        (1, "fall_winter", None),
        (2, "spring_summer", None),
        (2, "fall_winter", "avena_forrajera"),
    ]


@pytest.mark.parametrize(
    "rotation", [None, [], [{"year": 1, "season": "spring_summer", "crop_id": None}]]
)
def test_missing_current_rotation_is_an_error(provider, catalog, config, rotation):
    with pytest.raises(CurrentRotationRequiredError):
        run(provider, catalog, config, rotation=rotation)


def test_crop_outside_the_catalog_is_reported(provider, catalog, config):
    rotation = [{"year": 1, "season": "spring_summer", "crop_id": "algodon"}]
    with pytest.raises(UnknownCropError) as error:
        run(provider, catalog, config, rotation=rotation)
    assert error.value.crop_id == "algodon"


def test_saltillo_gets_alternatives_different_from_the_current(provider, catalog, config):
    result = run(provider, catalog, config)
    strategies = result["strategies"]
    assert strategies[0]["id"] == "current" and strategies[0]["is_current"]
    assert sum(strategy["is_current"] for strategy in strategies) == 1
    assert 3 <= len(strategies) <= 4
    sequences = [tuple(crops_of(strategy)) for strategy in strategies]
    assert len(set(sequences)) == len(sequences)
    assert {"legume", "cover"} <= set(by_id(result))
    assert "veza" in crops_of(by_id(result)["legume"]) or "frijol" in crops_of(
        by_id(result)["legume"]
    )


def test_excluded_crops_never_appear_in_alternatives(provider, catalog, config):
    constraints = Constraints(exclude_crops=frozenset({"veza", "sorgo"}))
    result = run(provider, catalog, config, constraints=constraints, max_strategies=6)
    for strategy in result["strategies"][1:]:
        assert not {"veza", "sorgo"} & set(crops_of(strategy))
    assert len(result["strategies"]) >= 3


def test_crops_needing_unavailable_equipment_are_skipped(provider, catalog, config):
    # Sin sembradora de grano fino no hay avena ni veza.
    constraints = Constraints(equipment=frozenset({"tractor", "planter", "combine"}))
    result = run(provider, catalog, config, constraints=constraints, max_strategies=6)
    for strategy in result["strategies"][1:]:
        assert not {"veza", "avena_forrajera"} & set(crops_of(strategy))


def test_forage_template_needs_declared_livestock(provider, catalog, config):
    without = run(provider, catalog, config, max_strategies=6)
    with_livestock = run(
        provider, catalog, config, constraints=Constraints(has_livestock=True), max_strategies=6
    )
    assert "forage" not in by_id(without)
    # El mejor forraje para el barbecho puede coincidir con la cobertura: entonces no se repite.
    forage = by_id(with_livestock).get("forage")
    cover = by_id(with_livestock)["cover"]
    assert forage is None or crops_of(forage) != crops_of(cover)


def test_drought_template_swaps_the_main_crop(provider, catalog, config):
    drought = by_id(run(provider, catalog, config, max_strategies=6))["drought"]
    assert crops_of(drought) == ["sorgo", None]
    assert drought["sequence"][0]["role"] == "drought_tolerant"
    sorghum = [{"year": 1, "season": "spring_summer", "crop_id": "sorgo"}]
    assert "drought" not in by_id(
        run(provider, catalog, config, rotation=sorghum, max_strategies=6)
    )


def test_max_strategies_keeps_the_current_and_the_best_alternatives(provider, catalog, config):
    full = run(provider, catalog, config, max_strategies=6)
    trimmed = run(provider, catalog, config, max_strategies=3)
    assert len(trimmed["strategies"]) == 3 and trimmed["strategies"][0]["is_current"]
    best = sorted(full["strategies"][1:], key=lambda s: -s["scores"]["overall"])[:2]
    assert {s["id"] for s in trimmed["strategies"][1:]} == {s["id"] for s in best}


def reduced_catalog(catalog, *crop_ids):
    return Catalog(
        [
            catalog.get(crop_id)
            for crop_id in ("maiz", "frijol", "sorgo", "avena_forrajera", "veza")
            if crop_id not in crop_ids
        ]
    )


def test_reduced_options_still_return_three_strategies(provider, catalog, config):
    # En La Laguna, sin riego, casi nada es plenamente apto: hay que relajar.
    result = run(
        provider,
        catalog,
        config,
        cell=LA_LAGUNA,
        field_context=FieldContext(),
        constraints=Constraints(exclude_crops=frozenset({"veza", "avena_forrajera"})),
    )
    assert len(result["strategies"]) >= 3
    relaxed = [s for s in result["strategies"][1:] if s["confidence"] == "low"]
    assert relaxed
    for strategy in relaxed:
        assert any(
            "se admite con condiciones" in risk or "barbecho" in risk
            for risk in strategy["risks_local_review"]
        )


def test_everything_excluded_falls_back_to_resting_the_soil(provider, catalog, config):
    everything = frozenset(crop.id for crop in catalog)
    result = run(provider, catalog, config, constraints=Constraints(exclude_crops=everything))
    assert [s["id"] for s in result["strategies"]] == ["current", "rest", "rest_early"] or len(
        result["strategies"]
    ) == 3
    rest = by_id(result)["rest"]
    assert rest["confidence"] == "low"
    assert any("barbecho" in risk for risk in rest["risks_local_review"])
    RotationResponse.model_validate({**result, "scenario": {}})


def test_relaxation_levels_are_tried_in_order(provider, catalog, config):
    strict = planner(provider, catalog, config)
    current = strict.current(MAIZE_FALLOW)
    assert all(candidate.relaxation == STRICT for candidate in strict.alternatives(current))
    blocked = planner(
        provider, catalog, config, Constraints(exclude_crops=frozenset(c.id for c in catalog))
    )
    assert all(
        candidate.relaxation == ANY_STATUS
        for candidate in blocked.alternatives(blocked.current(MAIZE_FALLOW))
    )


# ---------------------------------------------------------------- simulación


def metrics_of(provider, catalog, config, rotation, horizon=4, cell=SALTILLO):
    plan = planner(provider, catalog, config, cell=cell)
    return simulate(plan.current(rotation), cell_data(provider, cell).climatology, config, horizon)


def test_bare_soil_days_of_maize_fallow_match_the_manual_count(provider, catalog, config):
    metrics = metrics_of(provider, catalog, config, MAIZE_FALLOW)
    # Maíz: 125 días = 12 decenas con cultivo; quedan 24 de 36 decenas sin cultivo.
    assert metrics.bare_soil_days_per_year == round(24 * 365 / 36) == 243
    assert metrics.cover_fraction == pytest.approx(12 / 36)
    assert metrics.cycles_per_year == 1


def test_a_legume_raises_the_nitrogen_balance(provider, catalog, config):
    result = run(provider, catalog, config)
    current, legume = result["strategies"][0], by_id(result)["legume"]
    assert current["metrics"]["n_balance_kg_ha_per_year"] == -120
    assert legume["metrics"]["n_balance_kg_ha_per_year"] > -120
    assert any("nitrógeno" in reason for reason in legume["why"])


def test_a_cover_crop_reduces_bare_soil_and_erosion_exposure(provider, catalog, config):
    result = run(provider, catalog, config)
    current, cover = result["strategies"][0]["metrics"], by_id(result)["cover"]["metrics"]
    assert cover["bare_soil_days_per_year"] < current["bare_soil_days_per_year"]
    assert cover["erosion_exposure_index"] < current["erosion_exposure_index"]
    assert 0 <= cover["erosion_exposure_index"] <= 1
    assert cover["water_demand_mm_per_year"] > current["water_demand_mm_per_year"]


def test_water_metrics_reuse_the_suitability_balance(provider, catalog, config):
    metrics = metrics_of(provider, catalog, config, MAIZE_FALLOW)
    assert 0 < metrics.irrigation_need_mm_per_year < metrics.water_demand_mm_per_year
    two_cycles = MAIZE_FALLOW[:1] + [
        {"year": 1, "season": "fall_winter", "crop_id": "avena_forrajera"}
    ]
    assert metrics_of(provider, catalog, config, two_cycles).water_demand_mm_per_year > (
        metrics.water_demand_mm_per_year
    )


def test_same_family_every_season_has_the_minimum_pest_break(provider, catalog, config):
    grasses = [
        {"year": 1, "season": "spring_summer", "crop_id": "maiz"},
        {"year": 1, "season": "fall_winter", "crop_id": "avena_forrajera"},
        {"year": 2, "season": "spring_summer", "crop_id": "sorgo"},
    ]
    assert metrics_of(provider, catalog, config, grasses).pest_break_score == 0
    assert metrics_of(provider, catalog, config, MAIZE_BEAN).pest_break_score == 5
    assert pest_break_score([]) == 0


def test_margin_is_null_without_margin_index_and_used_when_present(provider, catalog, config):
    assert metrics_of(provider, catalog, config, MAIZE_BEAN).gross_margin_index is None
    priced = Catalog(
        [Crop.model_validate({**crop.model_dump(), "margin_index": 1.2}) for crop in catalog]
    )
    result = run(provider, priced, config)
    current = result["strategies"][0]
    assert current["metrics"]["gross_margin_index"] == 1.2
    assert current["scores"]["income"] == 4.0
    assert not any("margen" in gap for gap in current["gaps"])


def test_horizon_changes_only_how_the_sequence_repeats(provider, catalog, config):
    four = metrics_of(provider, catalog, config, MAIZE_BEAN, horizon=4)
    three = metrics_of(provider, catalog, config, MAIZE_BEAN, horizon=3)
    assert four.n_balance_kg_ha_per_year == round((-120 + 30) / 2)
    assert three.n_balance_kg_ha_per_year == round((-120 + 30 - 120) / 3)


# ---------------------------------------------------------------- puntaje


def test_save_water_priority_recommends_the_lowest_irrigation_need(provider, catalog, config):
    weights = {**dict.fromkeys(PRIORITIES, 0), "save_water": 5}
    result = run(provider, catalog, config, weights=weights, max_strategies=6)
    lowest = min(result["strategies"], key=lambda s: s["metrics"]["irrigation_need_mm_per_year"])
    assert result["recommended_id"] == lowest["id"]


def test_zero_weights_use_equal_weights(provider, catalog, config):
    zeros = run(provider, catalog, config, weights=dict.fromkeys(PRIORITIES, 0))
    equal = run(provider, catalog, config, weights=EQUAL)
    assert [s["scores"] for s in zeros["strategies"]] == [s["scores"] for s in equal["strategies"]]


def test_scores_stay_in_range_and_income_is_left_out_without_margin(provider, catalog, config):
    for strategy in run(provider, catalog, config, max_strategies=6)["strategies"]:
        scores = strategy["scores"]
        assert scores["income"] is None
        assert all(0 <= scores[name] <= 5 for name in PRIORITIES if name != "income")
        assert 0 <= scores["overall"] <= 100


def test_weights_move_the_overall_score(provider, catalog, config):
    metrics = metrics_of(provider, catalog, config, MAIZE_FALLOW)
    references = config.rotation.references
    water_only = score(metrics, {**dict.fromkeys(PRIORITIES, 0), "save_water": 5}, references)
    pests_only = score(metrics, {**dict.fromkeys(PRIORITIES, 0), "pest_break": 5}, references)
    assert water_only.overall == round(20 * water_only.save_water, 0) or water_only.overall > 0
    assert pests_only.overall == 0


def test_recommended_can_be_the_current_rotation(provider, catalog, config):
    weights = {**dict.fromkeys(PRIORITIES, 0), "low_labor": 5}
    result = run(provider, catalog, config, weights=weights)
    assert result["recommended_id"] == "current"


def test_relaxed_strategy_has_low_confidence(provider, catalog, config):
    everything = frozenset(crop.id for crop in catalog)
    relaxed = run(provider, catalog, config, constraints=Constraints(exclude_crops=everything))
    assert all(s["confidence"] == "low" for s in relaxed["strategies"][1:])
    normal = run(provider, catalog, config)
    assert normal["strategies"][0]["confidence"] == "medium"
    without_soil = CellData(cell_data(provider, SALTILLO).climatology, soil=())
    assert (
        run(provider, catalog, config, cell_data=without_soil)["strategies"][0]["confidence"]
        == "low"
    )


# ---------------------------------------------------------------- explicación


def test_every_rule_text_exists_in_both_languages():
    for key in rule_keys():
        assert set(MESSAGES[key]) == {"es", "en"}, key
        assert MESSAGES[key]["es"] != MESSAGES[key]["en"]
    assert len(rule_keys()) == len(set(rule_keys()))


@pytest.mark.parametrize("cell", [SALTILLO, LA_LAGUNA])
@pytest.mark.parametrize("language", ["es", "en"])
def test_every_strategy_is_fully_explained(provider, catalog, config, cell, language):
    context = FieldContext(irrigation_declared=True, irrigation_mm=400, language=language)
    result = run(
        provider,
        catalog,
        config,
        cell=cell,
        field_context=context,
        constraints=Constraints(has_livestock=True),
        irrigation_limit_mm=400,
        max_strategies=6,
    )
    sources = {source.source_id for source in provider.sources()}
    for strategy in result["strategies"]:
        for name in ("why", "evidence", "benefits", "gaps", "risks_local_review"):
            assert strategy[name], (strategy["id"], name)
        for evidence in strategy["evidence"]:
            assert evidence["source_id"] in sources
            assert re.search(r"\d", evidence["claim"])
        texts = [
            *strategy["why"],
            *strategy["benefits"],
            *strategy["gaps"],
            *strategy["risks_local_review"],
            *(evidence["claim"] for evidence in strategy["evidence"]),
        ]
        assert not [text for text in texts if "{" in text]
        assert not [
            t for t in texts if re.search(r"tu parcela tiene|your plot has|your field has", t)
        ]
    zonal = "celda de 9 km" if language == "es" else "9 km cell"
    assert all(zonal in strategy["gaps"][0] for strategy in result["strategies"])


def test_bare_soil_evidence_cites_the_days_and_a_source(provider, catalog, config):
    current = run(provider, catalog, config)["strategies"][0]
    evidence = next(e for e in current["evidence"] if "suelo descubierto" in e["claim"])
    assert "243 días" in evidence["claim"] and evidence["source_id"] == "nasa_power"


def test_irrigation_above_the_limit_is_a_risk_with_the_deficit(provider, catalog, config):
    result = run(provider, catalog, config, irrigation_limit_mm=400, max_strategies=6)
    for strategy in result["strategies"]:
        need = strategy["metrics"]["irrigation_need_mm_per_year"]
        risk = [r for r in strategy["risks_local_review"] if "tu límite es de 400 mm" in r]
        assert bool(risk) == (need > 400)
        if risk:
            assert f"Necesita {need} mm" in risk[0] and f"faltan {need - 400} mm" in risk[0]
    assert any(s["metrics"]["irrigation_need_mm_per_year"] > 400 for s in result["strategies"])


def test_minimum_gaps_and_risks_are_always_present(provider, catalog, config):
    for strategy in run(provider, catalog, config)["strategies"]:
        assert "celda de 9 km" in strategy["gaps"][0]
        assert "análisis de laboratorio" in strategy["gaps"][1]
        assert "agrónomo" in strategy["risks_local_review"][0]


def test_disclaimer_follows_the_language(provider, catalog, config):
    english = run(provider, catalog, config, field_context=FieldContext(language="en"))
    assert english["disclaimer"].startswith("Decision-support tool")
    assert "does not replace" in english["disclaimer"]
    assert all(s["risks_local_review"] for s in english["strategies"])
    assert "fallow" in english["strategies"][0]["name"]
    assert run(provider, catalog, config)["disclaimer"].startswith("Herramienta de apoyo")


def test_weak_crops_are_flagged_for_local_review(provider, catalog, config):
    current = run(provider, catalog, config, cell=LA_LAGUNA)["strategies"][0]
    assert any(
        "Maíz sembrado en mayo no es plenamente apto" in r for r in current["risks_local_review"]
    )


# ---------------------------------------------------------------- configuración y endpoint


def test_rotation_config_is_validated():
    import yaml

    from app.engines import config as engine_config

    document = yaml.safe_load(engine_config.DEFAULT_PATH.read_text(encoding="utf-8"))
    document["rotation"]["planting_months"]["spring_summer"] = 12
    with pytest.raises(EngineConfigError, match="planting_months.spring_summer"):
        parse_config(document)
    document = yaml.safe_load(engine_config.DEFAULT_PATH.read_text(encoding="utf-8"))
    document["rotation"]["om_trend"]["stable_from"] = 0.9
    with pytest.raises(EngineConfigError, match="stable_from"):
        parse_config(document)


@pytest.fixture
def rotating_field(client, headers):
    payload = field_payload(
        current_rotation=MAIZE_FALLOW,
        irrigation={"available": True, "source": "well", "max_mm_per_year": 400},
    )
    return client.post("/api/v1/fields", json=payload, headers=headers).json()


def test_rotations_endpoint_compares_strategies(client, headers, rotating_field):
    url = f"/api/v1/fields/{rotating_field['id']}/rotations"
    response = client.post(url, json={}, headers=headers)
    assert response.status_code == 200 and "x-fieldshift-mock" not in response.headers
    rotations = RotationResponse.model_validate(response.json())
    assert len(rotations.strategies) >= 3
    assert [s.is_current for s in rotations.strategies].count(True) == 1
    assert rotations.recommended_id in {s.id for s in rotations.strategies}
    assert rotations.scenario.delta_t_c == 0
    step = response.json()["strategies"][0]["sequence"][0]
    assert step == {
        "year": 1,
        "season": "spring_summer",
        "crop_id": "maiz",
        "role": "cash",
        "plant": "05-01",
        "harvest": "09-03",
    }
    sources = {source["id"] for source in client.get("/api/v1/sources").json()}
    for strategy in response.json()["strategies"]:
        assert {e["source_id"] for e in strategy["evidence"]} <= sources


def test_rotations_honour_the_request(client, headers, rotating_field):
    url = f"/api/v1/fields/{rotating_field['id']}/rotations"
    body = {
        "priorities": {
            "save_water": 5,
            "income": 0,
            "soil_health": 0,
            "forage": 0,
            "pest_break": 0,
            "low_labor": 0,
        },
        "constraints": {
            "exclude_crops": ["sorgo"],
            "irrigation_mm_per_year": 300,
            "horizon_years": 3,
        },
        "scenario": {"delta_t_c": 2, "delta_p_pct": -20},
        "max_strategies": 3,
    }
    response = client.post(url, json=body, headers={**headers, "Accept-Language": "en"})
    assert response.status_code == 200
    result = response.json()
    assert len(result["strategies"]) == 3 and result["scenario"] == {
        "delta_t_c": 2,
        "delta_p_pct": -20,
    }
    assert all("sorgo" not in crops_of(s) for s in result["strategies"])
    assert any(
        "your limit is 300 mm" in r for s in result["strategies"] for r in s["risks_local_review"]
    )
    assert result["disclaimer"].startswith("Decision-support tool")


def test_rotations_errors(client, headers, field, rotating_field):
    without = client.post(f"/api/v1/fields/{field['id']}/rotations", json={}, headers=headers)
    assert without.status_code == 422
    assert without.json()["error"]["code"] == "current_rotation_required"
    missing = "/api/v1/fields/fld_01KA0Z5T9M3X8Q2W4E6R7T8Y9A/rotations"
    assert client.post(missing, json={}, headers=headers).status_code == 404
    url = f"/api/v1/fields/{rotating_field['id']}/rotations"
    assert client.post(url, json={"max_strategies": 2}, headers=headers).status_code == 422
    assert (
        client.post(url, json={"priorities": {"save_water": 9}}, headers=headers).status_code == 422
    )
    unknown = field_payload(
        current_rotation=[{"year": 1, "season": "spring_summer", "crop_id": "algodon"}]
    )
    created = client.post("/api/v1/fields", json=unknown, headers=headers).json()
    response = client.post(f"/api/v1/fields/{created['id']}/rotations", json={}, headers=headers)
    assert response.status_code == 404 and response.json()["error"]["code"] == "crop_not_found"


def test_identical_requests_give_identical_bodies_quickly(client, headers, rotating_field):
    url = f"/api/v1/fields/{rotating_field['id']}/rotations"
    body = {"max_strategies": 6}
    first = client.post(url, json=body, headers=headers)
    started = time.perf_counter()
    second = client.post(url, json=body, headers=headers)
    assert time.perf_counter() - started < 1
    assert first.json() == second.json()


def test_every_response_metric_is_documented():
    text = DOCS.read_text(encoding="utf-8")
    for metric in StrategyMetrics.model_fields:
        assert f"`{metric}`" in text, metric
    for template in ("legume", "cover", "drought", "forage", "diversify", "rest"):
        assert f"`{template}`" in text, template
    assert dataclasses.is_dataclass(Constraints)
