"""Aptitud de un cultivo sembrado en un mes dado en la zona de una geocerca.

Motor determinista: cuatro factores (helada, calor, agua y suelo), cada uno con estado,
explicación y fuente, combinados en un puntaje de 0 a 100. Los umbrales y pesos están en
`config/engine.yaml`; las fórmulas, en docs/engines.md.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

from app.catalog.models import Crop
from app.data.models import ClimatologyDecade, SoilLayer
from app.engines.config import SuitabilityConfig
from app.engines.water import WaterBalance, water_balance
from app.i18n import translate

DECADES_PER_YEAR = 36
DAYS_PER_DECADE = 365 / DECADES_PER_YEAR
# Umbrales de calor que publica DATA (docs/data_contract.md §2).
HEAT_THRESHOLDS_C = (30, 32, 35, 38)
CLIMATE_SOURCE = "nasa_power"
SOIL_SOURCE = "soilgrids"
LAB_SOURCE = "lab_report"
FACTORS = ("frost", "heat", "water", "soil")
_DAYS_BEFORE_MONTH = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)


@dataclass(frozen=True)
class CellData:
    """Lo que el motor necesita de la celda. `climatology` trae las 36 decenas en orden."""

    climatology: Sequence[ClimatologyDecade]
    soil: Sequence[SoilLayer] = ()


@dataclass(frozen=True)
class FieldContext:
    """Lo que el agricultor declaró de su geocerca.

    `irrigation_declared` es falso cuando no dijo nada sobre el riego: se evalúa en temporal.
    `irrigation_mm` es el riego disponible por ciclo; `None` con riego declarado significa
    que no indicó un límite.
    """

    irrigation_declared: bool = False
    irrigation_mm: float | None = 0.0
    language: str = "es"
    # pH del análisis de laboratorio del agricultor; si existe, sustituye al estimado.
    lab_ph: float | None = None


@dataclass(frozen=True)
class FactorResult:
    factor: str
    status: str  # ok | warn | bad | unknown
    detail: str
    source_id: str | None
    score: float | None  # 0-100; `None` si el factor es desconocido


@dataclass(frozen=True)
class Evaluation:
    crop_id: str
    planting_month: int
    status: str  # suitable | marginal | unsuitable
    score: float
    harvest_window: tuple[str, str]
    reasons: tuple[FactorResult, ...]
    confidence: str
    water: WaterBalance | None = field(default=None, compare=False)

    def reason(self, factor: str) -> FactorResult:
        return next(reason for reason in self.reasons if reason.factor == factor)


# ---------------------------------------------------------------- calendario del ciclo


def cycle_days(crop: Crop) -> int:
    """Duración típica: el punto medio del rango del catálogo."""
    return round((crop.cycle_days[0] + crop.cycle_days[1]) / 2)


def occupied_decades(planting_month: int, days: int) -> list[int]:
    """Decenas (1-36) que ocupa un ciclo sembrado el día 1 del mes; cruza el fin de año."""
    first = (planting_month - 1) * 3
    count = max(1, min(DECADES_PER_YEAR, round(days / DAYS_PER_DECADE)))
    return [(first + offset) % DECADES_PER_YEAR + 1 for offset in range(count)]


def _month_day(day_of_year: int) -> str:
    day_of_year = (day_of_year - 1) % 365 + 1
    month = max(m for m in range(1, 13) if _DAYS_BEFORE_MONTH[m - 1] < day_of_year)
    return f"{month:02d}-{day_of_year - _DAYS_BEFORE_MONTH[month - 1]:02d}"


def harvest_window(planting_month: int, crop: Crop) -> tuple[str, str]:
    """Cosecha estimada (`MM-DD`) con el ciclo más corto y el más largo del cultivo."""
    planting_day = _DAYS_BEFORE_MONTH[planting_month - 1] + 1
    return (
        _month_day(planting_day + crop.cycle_days[0]),
        _month_day(planting_day + crop.cycle_days[1]),
    )


def flowering_decades(cycle: Sequence[int], window: tuple[float, float]) -> list[int]:
    start = math.floor(window[0] * len(cycle))
    end = max(start + 1, math.ceil(window[1] * len(cycle)))
    return list(cycle[start:end])


def nearest_heat_threshold(heat_critical_c: float) -> int:
    """Umbral publicado más cercano a la temperatura crítica; en empate, el más bajo."""
    return min(HEAT_THRESHOLDS_C, key=lambda t: (abs(t - heat_critical_c), t))


def decade_label(decade: int, language: str) -> str:
    """Primer día de la decena, por ejemplo "11 de enero" o "January 11"."""
    month = translate(f"month.{(decade - 1) // 3 + 1}", language)
    day = ((decade - 1) % 3) * 10 + 1
    return f"{month} {day}" if language == "en" else f"{day} de {month}"


# ---------------------------------------------------------------- factores


def _graded(value: float, warn: float, bad: float, worst: float, config: SuitabilityConfig):
    """Estado y puntaje de una magnitud en la que más es peor.

    100 en cero, `score_at_warn` en el umbral de aviso, `score_at_bad` en el de daño y 0 en
    `worst`, con tramos lineales entre ellos.
    """
    if value >= bad:
        span = max(worst - bad, 1e-9)
        score = config.score_at_bad * max(0.0, 1 - (value - bad) / span)
        return "bad", score
    if value >= warn:
        share = (value - warn) / (bad - warn)
        return "warn", config.score_at_warn - share * (config.score_at_warn - config.score_at_bad)
    share = value / warn if warn else 0.0
    return "ok", 100 - share * (100 - config.score_at_warn)


def _unknown(factor: str, language: str) -> FactorResult:
    return FactorResult(
        factor, "unknown", translate(f"suitability.{factor}.unknown", language), None, None
    )


def _frost(crop, rows, config: SuitabilityConfig, language: str) -> FactorResult:
    column = "frost_m2_prob" if crop.frost_tolerant else "frost_prob"
    if any(getattr(row, column) is None for row in rows):
        return _unknown("frost", language)
    worst = max(rows, key=lambda row: getattr(row, column))
    probability = getattr(worst, column)
    status, score = _graded(probability, config.frost.warn_prob, config.frost.bad_prob, 1.0, config)
    if crop.frost_tolerant:
        # Un cultivo tolerante aguanta heladas ligeras: solo cuentan las fuertes y nunca excluyen.
        if status == "bad":
            status, score = "warn", config.score_at_bad + 1
        key = "tolerant_ok" if status == "ok" else "tolerant_warn"
    else:
        key = status
    detail = translate(
        f"suitability.frost.{key}",
        language,
        pct=round(probability * 100),
        decade=decade_label(worst.decade, language),
        threshold=-2 if crop.frost_tolerant else 0,
    )
    return FactorResult("frost", status, detail, CLIMATE_SOURCE, score)


def _heat(crop, rows_by_decade, cycle, config: SuitabilityConfig, language: str) -> FactorResult:
    threshold = nearest_heat_threshold(crop.heat_critical_c)
    column = f"hot_prob_{threshold}"
    rows = [
        rows_by_decade[decade] for decade in flowering_decades(cycle, config.heat.flowering_window)
    ]
    if any(getattr(row, column) is None for row in rows):
        return _unknown("heat", language)
    worst = max(rows, key=lambda row: getattr(row, column))
    probability = getattr(worst, column)
    status, score = _graded(probability, config.heat.warn_prob, config.heat.bad_prob, 1.0, config)
    detail = translate(
        f"suitability.heat.{status}",
        language,
        pct=round(probability * 100),
        decade=decade_label(worst.decade, language),
        threshold=threshold,
        critical=f"{crop.heat_critical_c:g}",
    )
    return FactorResult("heat", status, detail, CLIMATE_SOURCE, score)


def _water(balance: WaterBalance | None, context: FieldContext, config: SuitabilityConfig):
    language = context.language
    if balance is None:
        return _unknown("water", language)
    water = config.water
    status, score = _graded(
        balance.deficit_fraction,
        water.warn_deficit_fraction,
        water.bad_deficit_fraction,
        1.0,
        config,
    )
    if not context.irrigation_declared:
        key = f"rainfed_{status}"
    elif context.irrigation_mm is None:
        key = "unlimited_irrigation"
    else:
        key = status
    detail = translate(
        f"suitability.water.{key}",
        language,
        demand=round(balance.demand_mm),
        rain=round(balance.effective_rain_mm),
        irrigation=round(balance.irrigation_mm),
        deficit=round(balance.deficit_mm),
    )
    return FactorResult("water", status, detail, CLIMATE_SOURCE, score)


def _soil(
    crop,
    layers: Sequence[SoilLayer],
    config: SuitabilityConfig,
    language: str,
    lab_ph: float | None = None,
):
    top = min(layers, key=lambda layer: layer.depth_top_cm, default=None)
    ph = lab_ph if lab_ph is not None else (top.ph if top is not None else None)
    if ph is None:
        return _unknown("soil", language)
    low, high = crop.ph
    distance = max(low - ph, ph - high, 0.0)
    tolerance = config.soil.ph_tolerance
    status, score = _graded(distance, tolerance / 2, tolerance, tolerance * 3, config)
    if distance == 0:
        status, score = "ok", 100.0
    difficult = top is not None and top.texture_class in config.soil.difficult_textures
    if difficult and status == "ok":
        status, score = "warn", config.score_at_warn
    key = "ph_ok" if distance == 0 else f"ph_{status}"
    if lab_ph is not None:
        key = "lab_" + key
    detail = translate(f"suitability.soil.{key}", language, ph=f"{ph:.1f}", low=low, high=high)
    if difficult:
        texture = translate("suitability.soil.texture", language, texture=top.texture_class)
        detail = f"{detail} {texture}"
    source = LAB_SOURCE if lab_ph is not None else SOIL_SOURCE
    return FactorResult("soil", status, detail, source, score)


# ---------------------------------------------------------------- evaluación


def evaluate(
    crop: Crop,
    planting_month: int,
    cell_data: CellData,
    field_context: FieldContext,
    scenario=None,
    *,
    config: SuitabilityConfig,
) -> Evaluation:
    """Evalúa sembrar `crop` en `planting_month` (1-12) con el clima y suelo de la celda.

    `scenario` queda reservado para `d4-scenarios`, que entrega `cell_data` ya ajustado.
    """
    rows_by_decade = {row.decade: row for row in cell_data.climatology}
    cycle = occupied_decades(planting_month, cycle_days(crop))
    rows = [rows_by_decade[decade] for decade in cycle]
    language = field_context.language
    balance = water_balance(
        crop,
        rows,
        field_context.irrigation_mm if field_context.irrigation_declared else 0.0,
        config.water,
    )
    reasons = (
        _frost(crop, rows, config, language),
        _heat(crop, rows_by_decade, cycle, config, language),
        _water(balance, field_context, config),
        _soil(crop, cell_data.soil, config, language, field_context.lab_ph),
    )
    known = [reason for reason in reasons if reason.score is not None]
    weight = sum(config.weights[reason.factor] for reason in known)
    score = (
        sum(config.weights[reason.factor] * reason.score for reason in known) / weight
        if weight
        else 0.0
    )
    if any(r.status == "bad" and r.factor in config.exclusive_factors for r in reasons):
        score = min(score, config.exclusive_score_cap)
    score = round(score)
    cuts = config.status_cuts
    status = (
        "suitable"
        if score >= cuts.suitable
        else "marginal"
        if score >= cuts.marginal
        else "unsuitable"
    )
    # Los datos son zonales (celda de 9 km): la confianza nunca es alta.
    confidence = "medium" if len(known) == len(reasons) else "low"
    return Evaluation(
        crop_id=crop.id,
        planting_month=planting_month,
        status=status,
        score=score,
        harvest_window=harvest_window(planting_month, crop),
        reasons=reasons,
        confidence=confidence,
        water=balance,
    )


def evaluate_matrix(
    crops: Sequence[Crop],
    cell_data: CellData,
    field_context: FieldContext,
    *,
    config: SuitabilityConfig,
) -> dict[str, list[Evaluation]]:
    """Las 12 evaluaciones (enero a diciembre) de cada cultivo, por `crop_id`."""
    return {
        crop.id: [
            evaluate(crop, month, cell_data, field_context, config=config) for month in range(1, 13)
        ]
        for crop in crops
    }
