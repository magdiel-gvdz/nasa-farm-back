"""Motor de rotaciones: genera, simula, puntúa y explica estrategias para una geocerca."""

from collections.abc import Mapping, Sequence
from dataclasses import asdict

from app.catalog.loader import Catalog
from app.engines.config import EngineConfig
from app.engines.rotation.candidates import (
    STRICT,
    Candidate,
    Constraints,
    CurrentRotationRequiredError,
    Planner,
    UnknownCropError,
)
from app.engines.rotation.explain import Context, explain, strategy_name
from app.engines.rotation.score import PRIORITIES, Scores, score
from app.engines.rotation.simulate import Metrics, simulate
from app.engines.suitability import CellData, FieldContext, _month_day
from app.i18n import translate

__all__ = ["Constraints", "CurrentRotationRequiredError", "UnknownCropError", "compare"]

_METRIC_FIELDS = (
    "water_demand_mm_per_year",
    "irrigation_need_mm_per_year",
    "n_balance_kg_ha_per_year",
    "om_trend",
    "erosion_exposure_index",
    "bare_soil_days_per_year",
    "pest_break_score",
    "gross_margin_index",
)
_DAYS_BEFORE_MONTH = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)


def _sequence(candidate: Candidate) -> list[dict]:
    steps = []
    for slot in candidate.slots:
        if slot.crop is None:
            steps.append(
                {
                    "year": slot.year,
                    "season": slot.season,
                    "crop_id": None,
                    "role": "bare",
                    "plant": None,
                    "harvest": None,
                }
            )
            continue
        planting_day = _DAYS_BEFORE_MONTH[slot.planting_month - 1] + 1
        cycle = round((slot.crop.cycle_days[0] + slot.crop.cycle_days[1]) / 2)
        steps.append(
            {
                "year": slot.year,
                "season": slot.season,
                "crop_id": slot.crop.id,
                "role": slot.role,
                "plant": f"{slot.planting_month:02d}-01",
                "harvest": _month_day(planting_day + cycle),
            }
        )
    return steps


def _confidence(candidate: Candidate) -> str:
    """La menor confianza de aptitud de sus cultivos; baja si hubo relajación."""
    if candidate.relaxation != STRICT:
        return "low"
    if any(slot.evaluation.confidence == "low" for slot in candidate.crop_slots):
        return "low"
    return "medium"


def compare(
    *,
    catalog: Catalog,
    cell_data: CellData,
    field_context: FieldContext,
    config: EngineConfig,
    current_rotation: Sequence[dict] | None,
    constraints: Constraints,
    weights: Mapping[str, int],
    irrigation_limit_mm: float | None,
    horizon_years: int = 4,
    max_strategies: int = 4,
) -> dict:
    """Estrategias comparadas, con la actual primero, y la recomendada.

    Lanza `CurrentRotationRequiredError` si no hay rotación actual y `UnknownCropError` si
    esta cita un cultivo que no está en el catálogo.
    """
    planner = Planner(catalog, cell_data, field_context, config, constraints)
    current = planner.current(current_rotation)
    language = field_context.language
    references = config.rotation.references

    def measured(candidate: Candidate) -> tuple[Candidate, Metrics, Scores]:
        metrics = simulate(candidate, cell_data.climatology, config, horizon_years)
        return candidate, metrics, score(metrics, weights, references)

    baseline = measured(current)
    alternatives = sorted(
        (measured(candidate) for candidate in planner.alternatives(current)),
        key=lambda item: -item[2].overall_exact,
    )[: max_strategies - 1]
    top_layer = min(cell_data.soil, key=lambda layer: layer.depth_top_cm, default=None)

    strategies = []
    for candidate, metrics, scores in (baseline, *alternatives):
        context = Context(
            candidate=candidate,
            metrics=metrics,
            baseline=baseline[1],
            irrigation_limit_mm=irrigation_limit_mm,
            soil_ph=top_layer.ph if top_layer else None,
            language=language,
        )
        strategies.append(
            {
                "id": candidate.id,
                "name": strategy_name(candidate, language),
                "is_current": candidate.is_current,
                "sequence": _sequence(candidate),
                "metrics": {name: getattr(metrics, name) for name in _METRIC_FIELDS},
                "scores": {
                    **{name: asdict(scores)[name] for name in PRIORITIES},
                    "overall": scores.overall,
                },
                **explain(context),
                "confidence": _confidence(candidate),
            }
        )
    ranked = [baseline, *alternatives]
    # En empate gana la primera: la rotación actual no se cambia sin una ventaja real.
    recommended = max(ranked, key=lambda item: item[2].overall_exact)[0]
    return {
        "strategies": strategies,
        "recommended_id": recommended.id,
        "disclaimer": translate("rotation.disclaimer", language),
    }
