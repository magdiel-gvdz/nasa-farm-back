"""Indicadores por decena recalculados desde la serie diaria, con las definiciones de DATA.

Implementa las definiciones de docs/fuentes_de_datos.md §8 y docs/data_contract.md §2: el
módulo de indicadores de DATA no está disponible para la API, así que la prueba de paridad
con la climatología publicada decide si son equivalentes.
"""

import math
from collections.abc import Sequence
from dataclasses import replace
from datetime import date

from app.data.models import ClimatologyDecade, DailyRow

# Umbrales de diseño de DATA (docs/data_contract.md §2).
FROST_C, HARD_FROST_C = 0.0, -2.0
HOT_C = (30, 32, 35, 38)
HEAVY_RAIN_MM = 25.0
VULNERABLE_FLOOR = 0.2
# Probabilidad que decide cada motivo de vulnerabilidad (el calor usa 35 °C).
VULNERABLE_REASONS = {
    "frost": "frost_prob",
    "heat": "hot_prob_35",
    "water_stress": "ws_prob",
    "heavy_rain": "heavy_rain_prob",
}


def decade_of(day: date) -> int:
    """Decena del año, de 1 a 36; la tercera de cada mes llega hasta fin de mes."""
    return (day.month - 1) * 3 + min((day.day - 1) // 10, 2) + 1


def extraterrestrial_radiation(lat_deg: float, day_of_year: int) -> float:
    """Ra en MJ/m²/día (FAO-56, ecuación 21)."""
    lat = math.radians(lat_deg)
    inverse_distance = 1 + 0.033 * math.cos(2 * math.pi * day_of_year / 365)
    declination = 0.409 * math.sin(2 * math.pi * day_of_year / 365 - 1.39)
    sunset = math.acos(max(-1.0, min(1.0, -math.tan(lat) * math.tan(declination))))
    return (
        (24 * 60 / math.pi)
        * 0.0820
        * inverse_distance
        * (
            sunset * math.sin(lat) * math.sin(declination)
            + math.cos(lat) * math.cos(declination) * math.sin(sunset)
        )
    )


def et0_hargreaves(lat_deg: float, day: date, tmax: float, tmin: float, tmean: float) -> float:
    """ET de referencia de un día en mm, Hargreaves-Samani (FAO-56, ecuación 52)."""
    radiation = extraterrestrial_radiation(lat_deg, day.timetuple().tm_yday)
    return 0.0023 * 0.408 * radiation * (tmean + 17.8) * math.sqrt(max(tmax - tmin, 0.0))


def percentile(values: Sequence[float], q: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * q / 100
    low = math.floor(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def decade_totals(
    daily: Sequence[DailyRow],
    lat_deg: float,
    years: Sequence[int],
    delta_t_c: float = 0.0,
    delta_p_pct: float = 0.0,
) -> dict[tuple[int, int], dict]:
    """Conteos y totales por (año, decena), con la serie desplazada por el escenario.

    `delta_t_c` se suma a las temperaturas ajustadas por altura y `delta_p_pct` multiplica la
    lluvia diaria. Los días sin temperatura o sin lluvia no cuentan para ese indicador.
    """
    wanted = set(years)
    factor = 1 + delta_p_pct / 100
    totals: dict[tuple[int, int], dict] = {}
    for row in daily:
        day = date.fromisoformat(row.date)
        if day.year not in wanted:
            continue
        key = (day.year, decade_of(day))
        bucket = totals.get(key)
        if bucket is None:
            bucket = totals[key] = {
                "frost": 0,
                "hard_frost": 0,
                **{f"hot_{t}": 0 for t in HOT_C},
                "precip": 0.0,
                "heavy": 0,
                "et0": 0.0,
            }
        if row.tmin_adj_c is not None:
            tmin = row.tmin_adj_c + delta_t_c
            bucket["frost"] += tmin < FROST_C
            bucket["hard_frost"] += tmin < HARD_FROST_C
        if row.tmax_adj_c is not None:
            tmax = row.tmax_adj_c + delta_t_c
            for threshold in HOT_C:
                bucket[f"hot_{threshold}"] += tmax > threshold
        if row.precip_mm is not None:
            precip = row.precip_mm * factor
            bucket["precip"] += precip
            bucket["heavy"] += precip > HEAVY_RAIN_MM
        if None not in (row.tmax_adj_c, row.tmin_adj_c, row.tmean_adj_c):
            bucket["et0"] += et0_hargreaves(
                lat_deg,
                day,
                row.tmax_adj_c + delta_t_c,
                row.tmin_adj_c + delta_t_c,
                row.tmean_adj_c + delta_t_c,
            )
    return totals


def recompute_climatology(
    base: Sequence[ClimatologyDecade],
    daily: Sequence[DailyRow],
    lat_deg: float,
    years: Sequence[int],
    delta_t_c: float = 0.0,
    delta_p_pct: float = 0.0,
) -> list[ClimatologyDecade]:
    """Climatología por decena con heladas, calor, lluvia y ET0 recalculados.

    La humedad del suelo, el suelo descubierto y el viento no dependen del escenario: se
    mantienen los de `base` (la climatología publicada).
    """
    totals = decade_totals(daily, lat_deg, years, delta_t_c, delta_p_pct)
    rows = []
    for row in base:
        decade_years = [
            totals[(year, row.decade)] for year in years if (year, row.decade) in totals
        ]
        if not decade_years:
            rows.append(row)
            continue

        def probability(column: str, values=decade_years) -> float:
            return round(sum(value[column] > 0 for value in values) / len(values), 1)

        precip = [value["precip"] for value in decade_years]
        et0 = [value["et0"] for value in decade_years]
        rows.append(
            replace(
                row,
                frost_prob=probability("frost"),
                frost_m2_prob=probability("hard_frost"),
                hot_prob_30=probability("hot_30"),
                hot_prob_32=probability("hot_32"),
                hot_prob_35=probability("hot_35"),
                hot_prob_38=probability("hot_38"),
                heavy_rain_prob=probability("heavy"),
                precip_p10=round(percentile(precip, 10), 3),
                precip_p50=round(percentile(precip, 50), 3),
                precip_p90=round(percentile(precip, 90), 3),
                et0_p50=round(percentile(et0, 50), 6),
                n_years=len(decade_years),
            )
        )
    return mark_vulnerable(rows)


def mark_vulnerable(rows: list[ClimatologyDecade]) -> list[ClimatologyDecade]:
    """Decena vulnerable: probabilidad sobre el percentil 75 de la celda y de al menos 0.2."""
    thresholds = {}
    for column in VULNERABLE_REASONS.values():
        known = [getattr(row, column) for row in rows if getattr(row, column) is not None]
        thresholds[column] = percentile(known, 75) if known else None
    marked = []
    for row in rows:
        reasons = [
            reason
            for reason, column in VULNERABLE_REASONS.items()
            if thresholds[column] is not None
            and getattr(row, column) is not None
            and getattr(row, column) > thresholds[column]
            and getattr(row, column) >= VULNERABLE_FLOOR
        ]
        marked.append(replace(row, vulnerable=bool(reasons), vulnerable_reasons=",".join(reasons)))
    return marked
