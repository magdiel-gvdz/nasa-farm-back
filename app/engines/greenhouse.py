"""Riesgo de que el viento dañe la estructura de un invernadero.

Ajusta una distribución de Gumbel por momentos a los máximos anuales del viento máximo diario
y compara la resistencia declarada por el fabricante con la ráfaga estimada. El dato es el
máximo de medias horarias de un modelo a ~55 km, no la ráfaga local: se declara siempre.
"""

import math
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from app.data.models import DailyRow
from app.engines.config import GreenhouseConfig
from app.i18n import translate

KMH_PER_MS = 3.6
RETURN_PERIODS = (10, 25, 50)
EULER_GAMMA = 0.5772


@dataclass(frozen=True)
class Gumbel:
    location: float  # μ
    scale: float  # β

    def return_level(self, period_years: int) -> float:
        """`x_T = μ − β·ln(−ln(1 − 1/T))`."""
        return self.location - self.scale * math.log(-math.log(1 - 1 / period_years))

    def exceedance_probability(self, value: float) -> float:
        """Probabilidad anual de que el máximo supere `value`."""
        return 1 - math.exp(-math.exp(-(value - self.location) / self.scale))


def fit_gumbel(maxima: Sequence[float]) -> Gumbel:
    """Ajuste por momentos: `β = √6·σ/π`, `μ = media − 0.5772·β`."""
    mean = sum(maxima) / len(maxima)
    variance = sum((value - mean) ** 2 for value in maxima) / (len(maxima) - 1)
    scale = math.sqrt(6 * variance) / math.pi
    return Gumbel(location=mean - EULER_GAMMA * scale, scale=scale)


def annual_maxima(daily: Sequence[DailyRow], min_days: int) -> dict[int, float]:
    """Máximo anual de `wind_max_ms` de los años con al menos `min_days` días con dato."""
    by_year: dict[int, list[float]] = defaultdict(list)
    for row in daily:
        if row.wind_max_ms is not None:
            by_year[int(row.date[:4])].append(row.wind_max_ms)
    return {
        year: max(values) for year, values in sorted(by_year.items()) if len(values) >= min_days
    }


def riskiest_months(daily: Sequence[DailyRow], count: int = 3) -> list[int]:
    """Meses con mayor máximo mensual medio de viento, del más ventoso al menos."""
    monthly: dict[tuple[int, int], float] = {}
    for row in daily:
        if row.wind_max_ms is None:
            continue
        key = (int(row.date[:4]), int(row.date[5:7]))
        monthly[key] = max(monthly.get(key, 0.0), row.wind_max_ms)
    by_month: dict[int, list[float]] = defaultdict(list)
    for (_, month), value in monthly.items():
        by_month[month].append(value)
    means = {month: sum(values) / len(values) for month, values in by_month.items()}
    return sorted(means, key=lambda month: (-means[month], month))[:count]


def _gap(code: str, severity: str, language: str, **params) -> dict:
    return {
        "code": code,
        "severity": severity,
        "message": translate(f"greenhouse.gap.{code}", language, **params),
    }


def assess(
    daily: Sequence[DailyRow],
    rated_wind_kmh: float | None,
    config: GreenhouseConfig,
    language: str,
) -> dict:
    """Bloque `wind` de la respuesta, más la confianza, los vacíos y las recomendaciones."""
    maxima = annual_maxima(daily, config.min_days_per_year)
    years = len(maxima)
    gaps = []
    months = riskiest_months(daily)
    month_names = ", ".join(translate(f"month.{month}", language) for month in months)
    if years < config.minimum_years:
        gaps.append(_gap("insufficient_wind_record", "high", language, years=years))
        gumbel = None
    else:
        gumbel = fit_gumbel([value * KMH_PER_MS for value in maxima.values()])
        if years < config.reliable_years:
            gaps.append(_gap("short_wind_record", "medium", language, years=years))
    levels = (
        [
            {
                "return_period_years": period,
                "sustained_kmh": round(gumbel.return_level(period), 1),
                "estimated_gust_kmh": round(gumbel.return_level(period) * config.gust_factor, 1),
            }
            for period in RETURN_PERIODS
        ]
        if gumbel
        else None
    )
    probability = status = None
    if rated_wind_kmh is None:
        gaps.append(_gap("no_rated_wind", "medium", language))
    elif gumbel is not None:
        # La estructura falla si la ráfaga (sostenido × factor) supera su resistencia.
        probability = round(gumbel.exceedance_probability(rated_wind_kmh / config.gust_factor), 4)
        status = (
            "ok"
            if probability < config.warn_probability
            else "warn"
            if probability <= config.bad_probability
            else "bad"
        )
    recommendations = [translate("greenhouse.recommend.manufacturer", language)]
    if months:
        recommendations.insert(
            0, translate("greenhouse.recommend.anchors", language, months=month_names)
        )
    if status in {"warn", "bad"}:
        recommendations.insert(
            0,
            translate(
                f"greenhouse.recommend.{status}",
                language,
                pct=round(probability * 100, 1),
                rated=round(rated_wind_kmh),
            ),
        )
    confidence = "medium" if gumbel and years >= config.reliable_years else "low"
    return {
        "wind": {
            "years_used": years,
            "gust_factor_assumed": config.gust_factor,
            "return_levels_kmh": levels,
            "rated_wind_kmh": rated_wind_kmh,
            "annual_exceedance_probability": probability,
            "status": status,
            "riskiest_months": months,
            "note": translate("greenhouse.wind_note", language),
        },
        "confidence": confidence,
        "gaps": gaps,
        "recommendations": recommendations,
    }
