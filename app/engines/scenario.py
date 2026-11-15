"""Escenarios hipotéticos de temperatura y lluvia.

Con un escenario distinto de cero, la climatología de la celda se recalcula desde la serie
diaria desplazada y los motores la usan sin saber que es un escenario. Con ambos cambios en
cero se usa la climatología publicada, así que el resultado es el de siempre.
"""

import threading
from collections import OrderedDict
from dataclasses import dataclass

from app.data import DataProvider, DataUnavailableError
from app.engines.indicators import recompute_climatology
from app.engines.suitability import CellData
from app.i18n import translate

CACHE_SIZE = 256
# Pasos de los controles del frontend: los escenarios se redondean a ellos.
DELTA_T_STEP_C = 0.5
DELTA_P_STEP_PCT = 5
# Lo que el escenario no cambia y se toma de los datos publicados.
NOT_RECOMPUTED = ("soil_moisture", "water_stress", "bare_soil", "wind", "soil")


class DailyUnavailableError(DataUnavailableError):
    """Sin serie diaria no se puede calcular un escenario."""


@dataclass(frozen=True)
class Scenario:
    delta_t_c: float = 0.0
    delta_p_pct: float = 0.0

    def rounded(self) -> "Scenario":
        return Scenario(
            round(self.delta_t_c / DELTA_T_STEP_C) * DELTA_T_STEP_C,
            round(self.delta_p_pct / DELTA_P_STEP_PCT) * DELTA_P_STEP_PCT,
        )

    @property
    def is_zero(self) -> bool:
        rounded = self.rounded()
        return rounded.delta_t_c == 0 and rounded.delta_p_pct == 0


@dataclass(frozen=True)
class ScenarioResult:
    cell_data: CellData
    scenario: Scenario
    daily_origin: str | None

    def describe(self, language: str) -> dict:
        """Bloque `scenario` de las respuestas."""
        if self.scenario.is_zero:
            return {
                "delta_t_c": 0.0,
                "delta_p_pct": 0.0,
                "daily_origin": None,
                "not_recomputed": [],
                "note": None,
            }
        return {
            "delta_t_c": self.scenario.delta_t_c,
            "delta_p_pct": self.scenario.delta_p_pct,
            "daily_origin": self.daily_origin,
            "not_recomputed": list(NOT_RECOMPUTED),
            "note": translate("scenario.note", language),
        }


class ScenarioService:
    """Climatologías de escenario por celda, versión de datos y escenario redondeado."""

    def __init__(self, provider: DataProvider):
        self._provider = provider
        self._cache: OrderedDict[tuple, ScenarioResult] = OrderedDict()
        self._lock = threading.Lock()
        self.computations = 0

    def apply(self, cell_id: str, base: CellData, scenario: Scenario) -> ScenarioResult:
        """Datos de la celda bajo el escenario. Lanza `DailyUnavailableError` sin serie diaria."""
        rounded = scenario.rounded()
        if rounded.is_zero:
            return ScenarioResult(base, Scenario(), None)
        key = (cell_id, self._provider.data_version(), rounded)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
        try:
            daily = self._provider.daily(cell_id)
        except DataUnavailableError as error:
            raise DailyUnavailableError(str(error)) from error
        if not daily:
            raise DailyUnavailableError(f"Sin serie diaria para la celda {cell_id}")
        cell = self._provider.cell(cell_id)
        # La misma ventana que los indicadores publicados (2016-2025).
        years = sorted({row.year for row in self._provider.years(cell_id)})
        climatology = recompute_climatology(
            base.climatology, daily, cell.lat, years, rounded.delta_t_c, rounded.delta_p_pct
        )
        self.computations += 1
        result = ScenarioResult(
            CellData(climatology=climatology, soil=base.soil),
            rounded,
            getattr(daily, "origin", None),
        )
        with self._lock:
            self._cache[key] = result
            while len(self._cache) > CACHE_SIZE:
                self._cache.popitem(last=False)
        return result
