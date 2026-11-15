import copy
import re
from functools import cache

ORIGIN = "http://localhost:5173"
SNAKE_CASE = re.compile(r"^[a-z][a-z0-9_]*$")
# Maíz en primavera-verano y barbecho en otoño-invierno.
MAIZE_FALLOW = [
    {"year": 1, "season": "spring_summer", "crop_id": "maiz"},
    {"year": 1, "season": "fall_winter", "crop_id": None},
]


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


def _suitability(crop_id: str | None) -> dict:
    from app.api.routes.suitability import cell_data, detail_response
    from app.catalog.loader import load_catalog
    from app.data.fixture import FixtureProvider
    from app.engines.config import load_config
    from app.engines.suitability import FieldContext, evaluate, evaluate_matrix

    config = load_config().suitability
    catalog = load_catalog()
    cell = cell_data(FixtureProvider(), "E9_r0463_c0846")
    if crop_id is not None:
        evaluation = evaluate(catalog.get(crop_id), 4, cell, FieldContext(), config=config)
        return {
            **detail_response(evaluation),
            "scenario": {
                "delta_t_c": 0.0,
                "delta_p_pct": 0.0,
                "daily_origin": None,
                "not_recomputed": [],
                "note": None,
            },
        }
    matrix = evaluate_matrix(list(catalog), cell, FieldContext(), config=config)
    return {
        "scenario": {
            "delta_t_c": 0.0,
            "delta_p_pct": 0.0,
            "daily_origin": None,
            "not_recomputed": [],
            "note": None,
        },
        "months": list(range(1, 13)),
        "crops": [
            {
                "crop_id": crop_id,
                "scores": [evaluation.score for evaluation in evaluations],
                "status": [evaluation.status for evaluation in evaluations],
            }
            for crop_id, evaluations in matrix.items()
        ],
    }


def reference_suitability_detail() -> dict:
    """Aptitud de maíz sembrado en abril en la celda de Saltillo, con datos sintéticos."""
    return _suitability("maiz")


def reference_suitability_matrix() -> dict:
    return _suitability(None)


def reference_rotations() -> dict:
    """Rotaciones de maíz-barbecho en la celda de Saltillo, con datos sintéticos."""
    from app.api.routes.suitability import cell_data
    from app.catalog.loader import load_catalog
    from app.data.fixture import FixtureProvider
    from app.engines.config import load_config
    from app.engines.rotation import Constraints, compare
    from app.engines.suitability import FieldContext

    result = compare(
        catalog=load_catalog(),
        cell_data=cell_data(FixtureProvider(), "E9_r0463_c0846"),
        field_context=FieldContext(),
        config=load_config(),
        current_rotation=MAIZE_FALLOW,
        constraints=Constraints(),
        weights={},
        irrigation_limit_mm=None,
    )
    return {
        **result,
        "scenario": {
            "delta_t_c": 0.0,
            "delta_p_pct": 0.0,
            "daily_origin": None,
            "not_recomputed": [],
            "note": None,
        },
    }
