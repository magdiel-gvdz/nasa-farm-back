"""Casos agronómicos con resultado evidente: protegen la demo de cambios tardíos en los motores.

Las instantáneas de `snapshots/` se regeneran con:
    python -m tests.engines.test_agronomy_cases
"""

import json
import sys
from pathlib import Path

import pytest

from app.api.routes.suitability import cell_data
from app.catalog.loader import load_catalog
from app.data.fixture import FixtureProvider
from app.engines.config import load_config
from app.engines.rotation import Constraints, compare
from app.engines.scenario import Scenario, ScenarioService
from app.engines.suitability import FieldContext, evaluate, evaluate_matrix
from tests.data.conformance import check_provider
from tests.engines.builders import BASE_CELL, BUILDERS

SNAPSHOTS = Path(__file__).resolve().parent / "snapshots"
DEMO_CELLS = {"saltillo": "E9_r0463_c0846", "la_laguna": "E9_r0461_c0822"}
RAINFED = FieldContext()
IRRIGATED = FieldContext(irrigation_declared=True, irrigation_mm=None)
MAIZE_FALLOW = [
    {"year": 1, "season": "spring_summer", "crop_id": "maiz"},
    {"year": 1, "season": "fall_winter", "crop_id": None},
]


@pytest.fixture(scope="module")
def catalog():
    return load_catalog()


@pytest.fixture(scope="module")
def config():
    return load_config()


def suit(provider, crop, month, context, config):
    return evaluate(crop, month, provider.cell_data(), context, config=config.suitability)


def rotations(data, catalog, config, rotation=MAIZE_FALLOW, **options):
    arguments = {
        "catalog": catalog,
        "cell_data": data,
        "field_context": IRRIGATED,
        "config": config,
        "current_rotation": rotation,
        "constraints": Constraints(),
        "weights": {},
        "irrigation_limit_mm": None,
        "max_strategies": 6,
    }
    arguments.update(options)
    return compare(**arguments)


# ---------------------------------------------------------------- constructores


@pytest.mark.parametrize("name", sorted(BUILDERS))
def test_each_builder_is_a_valid_provider(name):
    check_provider(BUILDERS[name]())


# ---------------------------------------------------------------- aptitud


def test_frost_never_rules_out_a_crop_where_it_never_freezes(catalog, config):
    provider = BUILDERS["frost_free"]()
    for crop in catalog:
        for month in range(1, 13):
            assert suit(provider, crop, month, IRRIGATED, config).reason("frost").status == "ok"


def test_frost_sensitive_crop_sown_in_december_with_frozen_winters_is_unsuitable(catalog, config):
    provider = BUILDERS["frozen_winters"]()
    for crop in catalog:
        evaluation = suit(provider, crop, 12, IRRIGATED, config)
        if crop.frost_tolerant:
            assert evaluation.reason("frost").status != "bad"
        else:
            assert evaluation.reason("frost").status == "bad"
            assert evaluation.status == "unsuitable"


def test_extreme_heat_at_flowering_is_bad_for_summer_crops(catalog, config):
    provider = BUILDERS["extreme_heat"]()
    for crop_id in ("maiz", "frijol", "sorgo"):
        heat = suit(provider, catalog.get(crop_id), 5, IRRIGATED, config).reason("heat")
        assert heat.status == "bad", crop_id


def test_without_rain_irrigation_makes_the_difference(catalog, config):
    provider = BUILDERS["no_rain"]()
    maize = catalog.get("maiz")
    rainfed = suit(provider, maize, 5, RAINFED, config)
    irrigated = suit(provider, maize, 5, IRRIGATED, config)
    assert rainfed.reason("water").status == "bad"
    assert rainfed.water.effective_rain_mm == 0
    assert irrigated.reason("water").status == "ok"
    assert irrigated.score > rainfed.score


def test_alkaline_soil_penalizes_crops_that_need_neutral_ph(catalog, config):
    provider = BUILDERS["alkaline_soil"]()
    for crop in catalog:
        soil = suit(provider, crop, 5, IRRIGATED, config).reason("soil")
        assert soil.status in {"warn", "bad"} and "8.8" in soil.detail


# ---------------------------------------------------------------- rotaciones


def test_a_legume_raises_the_nitrogen_balance(catalog, config):
    result = rotations(BUILDERS["frost_free"]().cell_data(), catalog, config)
    by_id = {strategy["id"]: strategy for strategy in result["strategies"]}
    current = by_id["current"]["metrics"]["n_balance_kg_ha_per_year"]
    assert by_id["legume"]["metrics"]["n_balance_kg_ha_per_year"] > current


def test_a_cover_crop_reduces_bare_soil_and_erosion_exposure(catalog, config):
    result = rotations(cell_data(FixtureProvider(), BASE_CELL), catalog, config)
    by_id = {strategy["id"]: strategy["metrics"] for strategy in result["strategies"]}
    assert by_id["cover"]["bare_soil_days_per_year"] < by_id["current"]["bare_soil_days_per_year"]
    assert by_id["cover"]["erosion_exposure_index"] < by_id["current"]["erosion_exposure_index"]


def test_the_same_family_every_season_has_the_minimum_pest_break(catalog, config):
    grasses = [
        {"year": 1, "season": "spring_summer", "crop_id": "maiz"},
        {"year": 1, "season": "fall_winter", "crop_id": "avena_forrajera"},
    ]
    result = rotations(cell_data(FixtureProvider(), BASE_CELL), catalog, config, rotation=grasses)
    assert result["strategies"][0]["metrics"]["pest_break_score"] == 0


def test_an_excluded_crop_never_appears(catalog, config):
    for excluded in ("veza", "frijol", "sorgo", "avena_forrajera"):
        result = rotations(
            cell_data(FixtureProvider(), BASE_CELL),
            catalog,
            config,
            constraints=Constraints(exclude_crops=frozenset({excluded})),
        )
        for strategy in result["strategies"][1:]:
            assert excluded not in {step["crop_id"] for step in strategy["sequence"]}


# ---------------------------------------------------------------- escenarios


def test_a_warmer_scenario_never_lowers_heat_nor_raises_frost():
    provider = FixtureProvider()
    service = ScenarioService(provider)
    base = cell_data(provider, BASE_CELL)
    warmer = service.apply(BASE_CELL, base, Scenario(2, 0)).cell_data
    for before, after in zip(base.climatology, warmer.climatology, strict=True):
        assert after.hot_prob_35 >= before.hot_prob_35
        assert after.frost_prob <= before.frost_prob


def test_less_rain_never_lowers_the_irrigation_need(catalog, config):
    provider = FixtureProvider()
    service = ScenarioService(provider)
    base = cell_data(provider, BASE_CELL)
    drier = service.apply(BASE_CELL, base, Scenario(0, -20)).cell_data
    before = rotations(base, catalog, config)["strategies"]
    after = {s["id"]: s for s in rotations(drier, catalog, config)["strategies"]}
    for strategy in before:
        if strategy["id"] in after:
            assert (
                after[strategy["id"]]["metrics"]["irrigation_need_mm_per_year"]
                >= strategy["metrics"]["irrigation_need_mm_per_year"]
            )


# ---------------------------------------------------------------- instantáneas de la demo


def demo_outputs() -> dict[str, dict]:
    """Matriz de aptitud y rotaciones de las dos geocercas de demostración (datos sintéticos)."""
    provider = FixtureProvider()
    catalog = load_catalog()
    config = load_config()
    context = FieldContext(irrigation_declared=True, irrigation_mm=400)
    outputs = {}
    for name, cell_id in DEMO_CELLS.items():
        data = cell_data(provider, cell_id)
        matrix = evaluate_matrix(list(catalog), data, context, config=config.suitability)
        outputs[f"{name}_suitability"] = {
            crop_id: [[evaluation.score, evaluation.status] for evaluation in evaluations]
            for crop_id, evaluations in matrix.items()
        }
        result = rotations(data, catalog, config, field_context=context, irrigation_limit_mm=400)
        outputs[f"{name}_rotations"] = result
    return outputs


def _render(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


@pytest.mark.parametrize("name", sorted(demo_outputs()))
def test_demo_outputs_match_their_snapshots(name):
    path = SNAPSHOTS / f"{name}.json"
    assert path.exists(), f"Falta {path.name}: python -m tests.engines.test_agronomy_cases"
    expected = path.read_text(encoding="utf-8")
    assert _render(demo_outputs()[name]) == expected, (
        f"{path.name} cambió. Si el cambio es intencionado, regenera las instantáneas con "
        "`python -m tests.engines.test_agronomy_cases` y revisa el diff."
    )


def write_snapshots() -> None:
    SNAPSHOTS.mkdir(exist_ok=True)
    for name, value in demo_outputs().items():
        (SNAPSHOTS / f"{name}.json").write_text(_render(value), encoding="utf-8", newline="\n")
        print(f"Instantánea: {name}.json")


if __name__ == "__main__":
    write_snapshots()
    sys.exit(0)
