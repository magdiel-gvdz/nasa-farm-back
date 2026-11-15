"""Simulación por decenas de una estrategia sobre el horizonte y sus métricas anuales."""

from collections.abc import Sequence
from dataclasses import dataclass

from app.data.models import ClimatologyDecade
from app.engines.config import EngineConfig
from app.engines.rotation.candidates import Candidate, Slot
from app.engines.suitability import DAYS_PER_DECADE, DECADES_PER_YEAR, cycle_days, occupied_decades
from app.engines.water import water_balance

_RESIDUE = {"low": 0.0, "medium": 0.5, "high": 1.0}


@dataclass(frozen=True)
class Metrics:
    water_demand_mm_per_year: float
    irrigation_need_mm_per_year: float
    n_balance_kg_ha_per_year: float
    om_trend: str
    erosion_exposure_index: float
    bare_soil_days_per_year: float
    pest_break_score: float
    gross_margin_index: float | None
    # Auxiliares para puntuar y explicar; no salen en la respuesta.
    forage_cycles_per_year: float = 0.0
    cycles_per_year: float = 0.0
    cover_fraction: float = 0.0


def horizon_slots(candidate: Candidate, horizon_years: int) -> list[Slot]:
    """La secuencia repetida hasta cubrir el horizonte."""
    by_year: dict[int, list[Slot]] = {}
    for slot in candidate.slots:
        by_year.setdefault(slot.year, []).append(slot)
    return [slot for year in range(horizon_years) for slot in by_year[year % candidate.years + 1]]


def covered_decades(slots: Sequence[Slot], horizon_years: int) -> list[bool]:
    """Qué decenas del horizonte tienen cultivo. El horizonte es cíclico: un ciclo de otoño
    del último año cubre el inicio del primero."""
    total = horizon_years * DECADES_PER_YEAR
    covered = [False] * total
    for index, slot in enumerate(slots):
        if slot.crop is None:
            continue
        year = index // 2
        for offset, _ in enumerate(occupied_decades(slot.planting_month, cycle_days(slot.crop))):
            first = year * DECADES_PER_YEAR + (slot.planting_month - 1) * 3
            covered[(first + offset) % total] = True
    return covered


def pest_break_score(slots: Sequence[Slot]) -> float:
    """De 0 a 5: fracción de cambios de cultivo en los que cambia la familia botánica."""
    families = [slot.crop.family for slot in slots if slot.crop is not None]
    if not families:
        return 0.0
    changes = sum(
        family != families[(index + 1) % len(families)] for index, family in enumerate(families)
    )
    return round(5 * changes / len(families), 1)


def simulate(
    candidate: Candidate,
    climatology: Sequence[ClimatologyDecade],
    config: EngineConfig,
    horizon_years: int,
) -> Metrics:
    slots = horizon_slots(candidate, horizon_years)
    crops = [slot for slot in slots if slot.crop is not None]
    rows = {row.decade: row for row in climatology}

    demand = need = 0.0
    for slot in crops:
        cycle = [rows[d] for d in occupied_decades(slot.planting_month, cycle_days(slot.crop))]
        # Sin riego: la necesidad de riego es lo que la lluvia efectiva no cubre.
        balance = water_balance(slot.crop, cycle, 0.0, config.suitability.water)
        if balance is not None:
            demand += balance.demand_mm
            need += balance.deficit_mm

    covered = covered_decades(slots, horizon_years)
    bare = [index for index, has_crop in enumerate(covered) if not has_crop]
    heavy_rain = [
        rows[index % DECADES_PER_YEAR + 1].heavy_rain_prob or 0.0 for index in range(len(covered))
    ]
    exposed = sum(heavy_rain[index] for index in bare)
    cover_fraction = 1 - len(bare) / len(covered)

    residue = sum(_RESIDUE[slot.crop.residue] for slot in crops) / len(crops) if crops else 0.0
    # La cobertura del suelo pesa más que el rastrojo.
    organic = 0.3 * residue + 0.7 * cover_fraction
    trend = config.rotation.om_trend
    om_trend = (
        "improving"
        if organic >= trend.improving_from
        else "stable"
        if organic >= trend.stable_from
        else "declining"
    )
    margins = [slot.crop.margin_index for slot in crops]
    return Metrics(
        water_demand_mm_per_year=round(demand / horizon_years),
        irrigation_need_mm_per_year=round(need / horizon_years),
        n_balance_kg_ha_per_year=round(sum(s.crop.n_balance_kg_ha for s in crops) / horizon_years),
        om_trend=om_trend,
        erosion_exposure_index=round(exposed / sum(heavy_rain), 2) if sum(heavy_rain) else 0.0,
        bare_soil_days_per_year=round(len(bare) * DAYS_PER_DECADE / horizon_years),
        pest_break_score=pest_break_score(slots),
        gross_margin_index=(
            round(sum(margins) / len(margins), 2)
            if margins and all(margin is not None for margin in margins)
            else None
        ),
        forage_cycles_per_year=sum("forage" in s.crop.roles for s in crops) / horizon_years,
        cycles_per_year=len(crops) / horizon_years,
        cover_fraction=cover_fraction,
    )
