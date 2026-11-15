"""Puntajes de 0 a 5 por prioridad y puntaje global de 0 a 100 de cada estrategia."""

from collections.abc import Mapping
from dataclasses import dataclass

from app.engines.config import RotationReferences
from app.engines.rotation.simulate import Metrics

PRIORITIES = ("save_water", "income", "soil_health", "forage", "pest_break", "low_labor")
_OM_SCORE = {"declining": 1.0, "stable": 3.0, "improving": 5.0}


@dataclass(frozen=True)
class Scores:
    save_water: float
    income: float | None
    soil_health: float
    forage: float
    pest_break: float
    low_labor: float
    overall: float
    # Sin redondear, para elegir la recomendada sin empates artificiales.
    overall_exact: float = 0.0


def _scale(value: float, worst: float, best: float) -> float:
    """0 en `worst`, 5 en `best`, lineal y acotado."""
    share = (value - worst) / (best - worst)
    return 5 * max(0.0, min(1.0, share))


def priority_scores(metrics: Metrics, references: RotationReferences) -> dict[str, float | None]:
    soil = (
        _scale(
            metrics.n_balance_kg_ha_per_year,
            references.n_balance_low_kg_ha,
            references.n_balance_high_kg_ha,
        )
        + _scale(metrics.bare_soil_days_per_year, 365, 0)
        + _scale(metrics.erosion_exposure_index, 1, 0)
        + _OM_SCORE[metrics.om_trend]
    ) / 4
    return {
        "save_water": _scale(metrics.irrigation_need_mm_per_year, references.irrigation_mm, 0),
        # Sin índice de margen en el catálogo la prioridad no se puede puntuar.
        "income": (
            None
            if metrics.gross_margin_index is None
            else _scale(metrics.gross_margin_index, 0, references.margin_index)
        ),
        "soil_health": soil,
        "forage": _scale(metrics.forage_cycles_per_year, 0, references.forage_cycles_per_year),
        "pest_break": metrics.pest_break_score,
        "low_labor": _scale(metrics.cycles_per_year, references.max_cycles_per_year, 1),
    }


def score(metrics: Metrics, weights: Mapping[str, int], references: RotationReferences) -> Scores:
    """Media de las prioridades ponderada por los pesos del agricultor (0 a 5).

    Con todos los pesos en cero se usan pesos iguales. Una prioridad sin puntaje no cuenta.
    """
    values = priority_scores(metrics, references)
    known = {name: value for name, value in values.items() if value is not None}
    applied = {name: weights.get(name, 0) for name in known}
    if not any(applied.values()):
        applied = dict.fromkeys(known, 1)
    overall = 20 * sum(applied[name] * known[name] for name in known) / sum(applied.values())
    return Scores(
        **{name: None if value is None else round(value, 1) for name, value in values.items()},
        overall=round(overall),
        overall_exact=overall,
    )
