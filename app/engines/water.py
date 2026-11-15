"""Balance de agua de un ciclo de cultivo: demanda, lluvia efectiva y déficit."""

from collections.abc import Sequence
from dataclasses import dataclass

from app.catalog.models import Crop
from app.data.models import ClimatologyDecade
from app.engines.config import WaterConfig


@dataclass(frozen=True)
class WaterBalance:
    demand_mm: float
    effective_rain_mm: float
    irrigation_mm: float
    deficit_mm: float

    @property
    def deficit_fraction(self) -> float:
        return self.deficit_mm / self.demand_mm if self.demand_mm else 0.0


def stage_coefficients(crop: Crop, n_decades: int, config: WaterConfig) -> list[float]:
    """Kc de cada decena del ciclo: inicial, media y final según `stage_fractions`."""
    fractions = config.stage_fractions
    coefficients = []
    for index in range(n_decades):
        position = (index + 0.5) / n_decades
        if position <= fractions.ini:
            coefficients.append(crop.kc.ini)
        elif position <= fractions.ini + fractions.mid:
            coefficients.append(crop.kc.mid)
        else:
            coefficients.append(crop.kc.end)
    return coefficients


def water_balance(
    crop: Crop,
    cycle: Sequence[ClimatologyDecade],
    irrigation_mm: float | None,
    config: WaterConfig,
) -> WaterBalance | None:
    """Balance del ciclo con la ET0 y la lluvia medianas de cada decena.

    `irrigation_mm` es el riego disponible en el ciclo; `None` significa que hay riego sin
    límite declarado, y entonces cubre lo que falte. Devuelve `None` si falta ET0 o lluvia.
    """
    if any(row.et0_p50 is None or row.precip_p50 is None for row in cycle):
        return None
    coefficients = stage_coefficients(crop, len(cycle), config)
    demand = sum(kc * row.et0_p50 for kc, row in zip(coefficients, cycle, strict=True))
    effective_rain = config.effective_rain_fraction * sum(row.precip_p50 for row in cycle)
    shortfall = max(0.0, demand - effective_rain)
    irrigation = shortfall if irrigation_mm is None else min(irrigation_mm, shortfall)
    return WaterBalance(
        demand_mm=demand,
        effective_rain_mm=effective_rain,
        irrigation_mm=irrigation,
        deficit_mm=shortfall - irrigation,
    )
