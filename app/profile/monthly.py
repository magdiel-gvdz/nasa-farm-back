"""Agregación de los indicadores por año y decena a resúmenes mensuales y anuales.

La probabilidad mensual de un evento es la fracción de años con al menos un evento en
cualquiera de las decenas del mes. No se obtiene sumando ni promediando las probabilidades
por decena, porque un mismo año puede tener el evento en varias decenas.
"""

import math
from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence

from app.data.models import DailyRow, IndicatorDecade

MONTHS = range(1, 13)


def mean(values: Iterable[float | None]) -> float | None:
    known = [value for value in values if value is not None]
    return sum(known) / len(known) if known else None


def percentile(values: Iterable[float | None], q: float) -> float | None:
    """Percentil con interpolación lineal; `None` si no hay valores."""
    ordered = sorted(value for value in values if value is not None)
    if not ordered:
        return None
    position = (len(ordered) - 1) * q / 100
    low = math.floor(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def trend_per_decade(years: Sequence[int], values: Sequence[float | None]) -> float | None:
    """Pendiente de la recta de mínimos cuadrados, expresada por cada 10 años."""
    pairs = [(year, value) for year, value in zip(years, values, strict=True) if value is not None]
    if len(pairs) < 5:
        return None
    mean_x = sum(year for year, _ in pairs) / len(pairs)
    mean_y = sum(value for _, value in pairs) / len(pairs)
    spread = sum((year - mean_x) ** 2 for year, _ in pairs)
    if spread == 0:
        return None
    slope = sum((year - mean_x) * (value - mean_y) for year, value in pairs) / spread
    return slope * 10


def rounded(value: float | None, digits: int = 1) -> float | None:
    return None if value is None else round(value, digits)


class MonthlyIndicators:
    """Indicadores de una celda agrupados por mes y año."""

    def __init__(self, indicators: Sequence[IndicatorDecade]):
        self._by_month: dict[int, dict[int, list[IndicatorDecade]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for row in indicators:
            self._by_month[row.month][row.year].append(row)
        self.years = sorted({row.year for row in indicators})

    def _yearly(
        self, month: int, value: Callable[[IndicatorDecade], float | None]
    ) -> list[float | None]:
        """Total del mes en cada año; `None` si ese año no tiene dato en ninguna decena."""
        totals = []
        for year in self.years:
            known = [v for v in map(value, self._by_month[month].get(year, [])) if v is not None]
            totals.append(sum(known) if known else None)
        return totals

    def share_of_years_with(self, month: int, column: str) -> float | None:
        """Fracción de años con al menos un evento en alguna decena del mes."""
        totals = [t for t in self._yearly(month, lambda row: getattr(row, column)) if t is not None]
        return sum(total > 0 for total in totals) / len(totals) if totals else None

    def mean_total(self, month: int, column: str) -> float | None:
        return mean(self._yearly(month, lambda row: getattr(row, column)))

    def percentile_total(self, month: int, column: str, q: float) -> float | None:
        return percentile(self._yearly(month, lambda row: getattr(row, column)), q)

    def weighted_mean(self, month: int, column: str) -> float | None:
        """Media del mes ponderada por los días de cada decena (para temperaturas)."""
        weighted, days = 0.0, 0
        for rows in self._by_month[month].values():
            for row in rows:
                value = getattr(row, column)
                if value is not None:
                    weighted += value * row.n_days
                    days += row.n_days
        return weighted / days if days else None

    def mean_growing_degree_days(self, month: int, base_c: float = 10.0) -> float | None:
        def degree_days(row: IndicatorDecade) -> float | None:
            if row.tmax_mean is None or row.tmin_mean is None:
                return None
            return row.n_days * max(0.0, (row.tmax_mean + row.tmin_mean) / 2 - base_c)

        return mean(self._yearly(month, degree_days))

    def mean_of_decade_values(self, month: int, column: str) -> float | None:
        return mean(getattr(row, column) for rows in self._by_month[month].values() for row in rows)

    def max_of(self, month: int, column: str) -> float | None:
        values = [
            getattr(row, column)
            for rows in self._by_month[month].values()
            for row in rows
            if getattr(row, column) is not None
        ]
        return max(values) if values else None


class DailyRecords:
    """Lo que solo se puede saber de la serie diaria: récords, viento diario y fechas de helada."""

    def __init__(self, daily: Sequence[DailyRow], frost_threshold_c: float):
        self._by_month: dict[int, list[DailyRow]] = defaultdict(list)
        self._frost_days: dict[int, list[int]] = defaultdict(list)
        self.years: set[int] = set()
        for row in daily:
            year, month, day = (int(part) for part in row.date.split("-"))
            self._by_month[month].append(row)
            self.years.add(year)
            if row.tmin_adj_c is not None and row.tmin_adj_c < frost_threshold_c:
                self._frost_days[year].append(_day_of_year(year, month, day))

    def __bool__(self) -> bool:
        return bool(self.years)

    def record(self, month: int, column: str, pick: Callable = max) -> float | None:
        values = [getattr(row, column) for row in self._by_month[month]]
        known = [value for value in values if value is not None]
        return pick(known) if known else None

    def mean_of(self, month: int, column: str) -> float | None:
        return mean(getattr(row, column) for row in self._by_month[month])

    def frost_dates(self) -> dict | None:
        """Última helada de primavera, primera de otoño y días libres de helada entre ambas."""
        if not self.years:
            return None
        spring, fall, free = [], [], []
        for year in sorted(self.years):
            days = self._frost_days.get(year, [])
            last_spring = max((day for day in days if day <= 182), default=None)
            first_fall = min((day for day in days if day > 182), default=None)
            if last_spring is not None:
                spring.append(last_spring)
            if first_fall is not None:
                fall.append(first_fall)
            free.append((first_fall or 366) - (last_spring or 0) - 1)
        without_frost = sum(not self._frost_days.get(year) for year in self.years)
        return {
            "last_spring_frost": _date_percentiles(spring),
            "first_fall_frost": _date_percentiles(fall),
            "frost_free_days": {
                "p10": round(percentile(free, 10)),
                "p50": round(percentile(free, 50)),
            },
            "share_years_without_frost": round(without_frost / len(self.years), 2),
        }


_DAYS_BEFORE_MONTH = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _day_of_year(year: int, month: int, day: int) -> int:
    return _DAYS_BEFORE_MONTH[month - 1] + day + (1 if month > 2 and _is_leap(year) else 0)


def month_day(day_of_year: int) -> str:
    """`MM-DD` de un día del año en un año no bisiesto."""
    day_of_year = max(1, min(365, day_of_year))
    month = max(m for m in MONTHS if _DAYS_BEFORE_MONTH[m - 1] < day_of_year)
    return f"{month:02d}-{day_of_year - _DAYS_BEFORE_MONTH[month - 1]:02d}"


def _date_percentiles(days: list[int]) -> dict | None:
    # Con menos de tres años con helada los percentiles no dicen nada.
    if len(days) < 3:
        return None
    result = {}
    for name, q in (("p10", 10), ("p50", 50), ("p90", 90)):
        day = round(percentile(days, q))
        result[name] = {"doy": day, "date": month_day(day)}
    return result


def decade_start(decade: int) -> str:
    """`MM-DD` del primer día de la decena (días 1, 11 y 21 de cada mes)."""
    return f"{(decade - 1) // 3 + 1:02d}-{((decade - 1) % 3) * 10 + 1:02d}"


def gumbel_return_level(annual_maxima: Sequence[float], return_period_years: int) -> float | None:
    """Nivel de retorno con una Gumbel ajustada por momentos a los máximos anuales."""
    if len(annual_maxima) < 5:
        return None
    center = sum(annual_maxima) / len(annual_maxima)
    variance = sum((value - center) ** 2 for value in annual_maxima) / (len(annual_maxima) - 1)
    scale = math.sqrt(variance * 6) / math.pi
    location = center - 0.5772 * scale
    return location - scale * math.log(-math.log(1 - 1 / return_period_years))
