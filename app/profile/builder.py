"""Convierte los datos de DATA de una celda en el `FieldProfile` del contrato."""

from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime

from app.data import DataProvider, DataUnavailableError
from app.data.models import Cell, ClimatologyDecade, IndicatorYear
from app.data.models import SoilLayer as SoilRow
from app.geo.grid import CELL_M
from app.profile.gaps import ProfileFacts, build_gaps
from app.profile.monthly import (
    MONTHS,
    DailyRecords,
    MonthlyIndicators,
    decade_start,
    gumbel_return_level,
    mean,
    percentile,
    rounded,
    trend_per_decade,
)

PIPELINE_VERSION = "profile-v1"

# Umbrales con los que DATA calcula los indicadores (docs/data_contract.md §2).
FROST_C, SEVERE_FROST_C = 0.0, -2.0
HEAT_THRESHOLDS_C = (30, 32, 35, 38)
HEAVY_RAIN_MM = 25.0
# Racha estimada = viento sostenido máximo × factor; es un supuesto, no una medición.
GUST_FACTOR = 1.4
KMH_PER_MS = 3.6
# Suelo descubierto: la mayoría de los años con NDVI bajo en la decena.
BARE_SOIL_PROB = 0.5

CLIMATE_SOURCE = "nasa_power"
SOIL_SOURCE = "soilgrids"
ELEVATION_SOURCE = "copernicus_dem_glo90"
NDVI_SOURCE = "modis_ndvi"
SOIL_MOISTURE_SOURCES = {"smap_l4": "smap_l4", "power_gwetroot": CLIMATE_SOURCE}
SOIL_UNCERTAINTY = {
    "soc_g_kg": "soc_g_kg",
    "n_total_g_kg": "nitrogen_g_kg",
    "ph": "ph",
    "cec_cmol_kg": "cec_cmol_kg",
    "clay_pct": "clay_pct",
    "sand_pct": "sand_pct",
    "silt_pct": "silt_pct",
    "bulk_density_g_cm3": "bdod_kg_dm3",
}


def _frost(monthly: MonthlyIndicators, daily: DailyRecords) -> dict:
    return {
        "threshold_c": FROST_C,
        "severe_threshold_c": SEVERE_FROST_C,
        "years_analyzed": len(monthly.years),
        "last_spring_frost": None,
        "first_fall_frost": None,
        "frost_free_days": None,
        "share_years_without_frost": None,
        **(daily.frost_dates() or {}),
        "by_month": [
            {
                "month": month,
                "prob_any_frost": rounded(monthly.share_of_years_with(month, "frost_days"), 2) or 0,
                "mean_frost_days": rounded(monthly.mean_total(month, "frost_days")),
                "mean_severe_frost_days": rounded(monthly.mean_total(month, "frost_days_m2")),
                "record_tmin_c": rounded(daily.record(month, "tmin_adj_c", min)),
            }
            for month in MONTHS
        ],
    }


def _rain(monthly: MonthlyIndicators, years: Sequence[IndicatorYear]) -> dict:
    by_month = [
        {
            "month": month,
            "mean_mm": rounded(monthly.mean_total(month, "precip_mm")) or 0,
            "p20_mm": rounded(monthly.percentile_total(month, "precip_mm", 20)),
            "p80_mm": rounded(monthly.percentile_total(month, "precip_mm", 80)),
            "mean_heavy_rain_days": rounded(monthly.mean_total(month, "heavy_rain_days"), 2),
        }
        for month in MONTHS
    ]
    annual = [row.precip_mm for row in years]
    annual_mean = mean(annual) or 0
    known = [value for value in annual if value is not None]
    deviation = (
        (sum((value - annual_mean) ** 2 for value in known) / (len(known) - 1)) ** 0.5
        if len(known) > 1
        else None
    )
    return {
        "source_id": CLIMATE_SOURCE,
        "annual_mean_mm": rounded(annual_mean),
        "annual_p20_mm": rounded(percentile(annual, 20)),
        "annual_p80_mm": rounded(percentile(annual, 80)),
        "annual_cv": rounded(deviation / annual_mean, 2) if deviation and annual_mean else None,
        "trend_mm_per_decade": rounded(trend_per_decade([row.year for row in years], annual)),
        # Meses que aportan más que un reparto uniforme de la lluvia anual.
        "rainy_months": [
            entry["month"] for entry in by_month if entry["mean_mm"] > annual_mean / 12
        ],
        "heavy_rain_threshold_mm": HEAVY_RAIN_MM,
        "by_month": by_month,
    }


def _heat(monthly: MonthlyIndicators, years: Sequence[IndicatorYear], daily: DailyRecords) -> dict:
    by_month = [
        {
            "month": month,
            "mean_tmax_c": rounded(monthly.weighted_mean(month, "tmax_mean")) or 0,
            "mean_tmin_c": rounded(monthly.weighted_mean(month, "tmin_mean")) or 0,
            "record_tmax_c": rounded(daily.record(month, "tmax_adj_c")),
            "mean_gdd_base10": rounded(monthly.mean_growing_degree_days(month), 0),
            **{
                f"mean_days_over_{threshold}c": rounded(
                    monthly.mean_total(month, f"hot_days_{threshold}")
                )
                for threshold in HEAT_THRESHOLDS_C
            },
        }
        for month in MONTHS
    ]
    annual = [
        (row.tmax_mean + row.tmin_mean) / 2
        if row.tmax_mean is not None and row.tmin_mean is not None
        else None
        for row in years
    ]
    degree_days = [entry["mean_gdd_base10"] for entry in by_month]
    return {
        "thresholds_c": list(HEAT_THRESHOLDS_C),
        "annual_mean_c": rounded(mean(annual)) or 0,
        "trend_c_per_decade": rounded(trend_per_decade([row.year for row in years], annual), 2),
        "hottest_month": max(by_month, key=lambda entry: entry["mean_tmax_c"])["month"],
        "annual_gdd_base10": (
            sum(degree_days) if all(v is not None for v in degree_days) else None
        ),
        "by_month": by_month,
    }


def _wind(
    monthly: MonthlyIndicators, years: Sequence[IndicatorYear], daily: DailyRecords
) -> dict | None:
    annual_maxima = [row.wind_max_ms * KMH_PER_MS for row in years if row.wind_max_ms is not None]
    if not annual_maxima:
        return None
    by_month = []
    for month in MONTHS:
        # Con serie diaria, la media del máximo diario; sin ella, la del máximo por decena.
        typical = daily.mean_of(month, "wind_max_ms") if daily else None
        if typical is None:
            typical = monthly.mean_of_decade_values(month, "wind_max_ms")
        record = monthly.max_of(month, "wind_max_ms")
        by_month.append(
            {
                "month": month,
                "mean_daily_max_kmh": rounded((typical or 0) * KMH_PER_MS),
                "record_kmh": rounded(record * KMH_PER_MS) if record is not None else None,
            }
        )
    return_levels = []
    for period in (10, 25, 50):
        level = gumbel_return_level(annual_maxima, period)
        if level is not None:
            return_levels.append(
                {
                    "return_period_years": period,
                    "sustained_kmh": rounded(level),
                    "estimated_gust_kmh": rounded(level * GUST_FACTOR),
                }
            )
    return {
        "annual_max_mean_kmh": rounded(mean(annual_maxima)),
        "record_kmh": rounded(max(annual_maxima)),
        "windiest_month": max(by_month, key=lambda entry: entry["mean_daily_max_kmh"])["month"],
        "gust_factor_assumed": GUST_FACTOR,
        "return_levels_kmh": return_levels,
        "by_month": by_month,
    }


def _risk_calendar(climatology: Sequence[ClimatologyDecade]) -> list[dict]:
    return [
        {
            "decade": row.decade,
            "month": row.month,
            "starts": decade_start(row.decade),
            "p_frost": row.frost_prob,
            "p_frost_severe": row.frost_m2_prob,
            "p_heat_30c": row.hot_prob_30,
            "p_heat_32c": row.hot_prob_32,
            "p_heat_35c": row.hot_prob_35,
            "p_heat_38c": row.hot_prob_38,
            "p_heavy_rain": row.heavy_rain_prob,
            "p_water_stress": row.ws_prob,
            "p_bare_soil": row.bare_prob,
            "p_strong_wind": row.windy_prob,
            "precip_p50_mm": rounded(row.precip_p50),
            "et0_p50_mm": rounded(row.et0_p50),
            "vulnerable": row.vulnerable,
            "vulnerable_reasons": [r for r in row.vulnerable_reasons.split(",") if r],
        }
        for row in climatology
    ]


def _soil(layers: Sequence[SoilRow]) -> dict | None:
    if not layers:
        return None
    return {
        "source_id": SOIL_SOURCE,
        # SoilGrids es una estimación global a 250 m promediada en la celda.
        "confidence": "medium",
        "texture_class": layers[0].texture_class,
        "layers": [
            {
                "depth_cm": [row.depth_top_cm, row.depth_bottom_cm],
                "soc_g_kg": rounded(row.soc_g_kg),
                "om_pct": rounded(row.om_pct_est, 2),
                "n_total_g_kg": rounded(row.nitrogen_g_kg, 2),
                "ph": rounded(row.ph),
                "cec_cmol_kg": rounded(row.cec_cmol_kg),
                "clay_pct": rounded(row.clay_pct),
                "sand_pct": rounded(row.sand_pct),
                "silt_pct": rounded(row.silt_pct),
                "bulk_density_g_cm3": rounded(row.bdod_kg_dm3, 2),
                "awc_mm_per_m": rounded(row.awc_mm_per_m),
                "uncertainty": {
                    name: {
                        "p05": rounded(getattr(row, f"{column}_p05"), 2),
                        "p95": rounded(getattr(row, f"{column}_p95"), 2),
                    }
                    for name, column in SOIL_UNCERTAINTY.items()
                    if getattr(row, f"{column}_p05") is not None
                    and getattr(row, f"{column}_p95") is not None
                },
            }
            for row in layers
        ],
        "lab": None,
        "k_factor": rounded(layers[0].k_factor, 3),
    }


def _terrain(cell: Cell) -> dict | None:
    if cell.cell_elev_m is None:
        return None
    return {
        "source_id": ELEVATION_SOURCE,
        "elevation_m": {"mean": rounded(cell.cell_elev_m), "min": None, "max": None},
        "slope_pct": None,
        "aspect_dominant": None,
        "cold_air_pooling_share": None,
    }


def _water(
    monthly: MonthlyIndicators,
    climatology: Sequence[ClimatologyDecade],
    moisture_source: str | None,
) -> dict:
    def moisture(month: int, column: str) -> float | None:
        return rounded(mean(getattr(row, column) for row in climatology if row.month == month))

    has_moisture = any(row.smp_p50 is not None for row in climatology)
    return {
        "soil_moisture": (
            {
                "source_id": moisture_source,
                "years": [monthly.years[0], monthly.years[-1]],
                "by_month": [
                    {
                        "month": month,
                        "mean_m3_m3": None,
                        "percentile_p10": moisture(month, "smp_p10"),
                        "percentile_p50": moisture(month, "smp_p50"),
                        "percentile_p90": moisture(month, "smp_p90"),
                    }
                    for month in MONTHS
                ],
            }
            if has_moisture and moisture_source
            else None
        ),
        "et": {
            "source_id": CLIMATE_SOURCE,
            "method": "Hargreaves-Samani (FAO-56)",
            "by_month": [
                {
                    "month": month,
                    "et_mm": None,
                    "et0_mm": rounded(monthly.mean_total(month, "et0_mm")) or 0,
                }
                for month in MONTHS
            ],
        },
        "water_balance_by_month": [
            {
                "month": month,
                "p_minus_et0_mm": rounded(monthly.mean_total(month, "p_minus_et0_mm")) or 0,
            }
            for month in MONTHS
        ],
        "groundwater": None,
    }


def _vegetation(
    monthly: MonthlyIndicators, climatology: Sequence[ClimatologyDecade]
) -> dict | None:
    ndvi = {month: monthly.mean_of_decade_values(month, "ndvi_mean") for month in MONTHS}
    if any(value is None for value in ndvi.values()):
        return None
    bare_decades = [
        row.decade
        for row in climatology
        if row.bare_prob is not None and row.bare_prob >= BARE_SOIL_PROB
    ]
    bare_by_month = Counter((decade - 1) // 3 + 1 for decade in bare_decades)
    return {
        "source_id": NDVI_SOURCE,
        "ndvi_by_month": [
            {"month": month, "mean": rounded(ndvi[month], 2), "p10": None, "p90": None}
            for month in MONTHS
        ],
        "bare_soil_months": [month for month in MONTHS if bare_by_month[month] >= 2],
        "bare_soil_decades": bare_decades,
        "vigor_trend_per_decade": None,
    }


def _referenced_sources(node: object) -> set[str]:
    if isinstance(node, dict):
        found = {node["source_id"]} if isinstance(node.get("source_id"), str) else set()
        return found.union(*(_referenced_sources(value) for value in node.values()))
    if isinstance(node, list):
        return set().union(*(_referenced_sources(value) for value in node))
    return set()


def _sources(provider: DataProvider, body: dict) -> list[dict]:
    referenced = _referenced_sources(body)
    return [
        {
            "id": source.source_id,
            "name": source.name,
            "organization": source.organization,
            "product": source.product_version,
            "url": source.url,
            "resolution": source.resolution,
            "period": source.period,
            "license": source.license,
            "data_class": source.data_class,
        }
        for source in provider.sources()
        if source.source_id in referenced
    ]


def build_profile(provider: DataProvider, cell_id: str, language: str) -> dict:
    """Perfil de la celda, sin `field_id`. Lanza `UnknownCellError` si la celda no existe."""
    cell = provider.cell(cell_id)
    indicators = provider.indicators(cell_id)
    climatology = provider.climatology(cell_id)
    years = provider.years(cell_id)
    monthly = MonthlyIndicators(indicators)
    try:
        daily_rows = provider.daily(cell_id)
    except DataUnavailableError:
        # Sin serie diaria no hay récords ni fechas de helada, pero el perfil sigue.
        daily_rows = ()
    daily = DailyRecords(daily_rows, FROST_C)

    sources_used = Counter(row.sm_src for row in indicators if row.sm_src)
    moisture_source = (
        SOIL_MOISTURE_SOURCES.get(sources_used.most_common(1)[0][0]) if sources_used else None
    )
    wind = _wind(monthly, years, daily)
    soil = _soil(provider.soil(cell_id))
    vegetation = _vegetation(monthly, climatology)
    body = {
        "status": "ready",
        "cell_id": cell.cell_id,
        "zone_id": cell.zone_id,
        "resolution_m": round(CELL_M),
        "computed_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pipeline_version": PIPELINE_VERSION,
        "data_version": provider.data_version(),
        "climate": {
            "source_id": CLIMATE_SOURCE,
            "years": [monthly.years[0], monthly.years[-1]],
            "elevation_m": rounded(cell.cell_elev_m),
            "frost": _frost(monthly, daily),
            "rain": _rain(monthly, years),
            "heat": _heat(monthly, years, daily),
            "wind": wind,
            "light": None,
            "risk_calendar": _risk_calendar(climatology),
        },
        "soil": soil,
        "terrain": _terrain(cell),
        "water": _water(monthly, climatology, moisture_source),
        "vegetation": vegetation,
        "land_use": None,
        "hazards": {"hail": None},
    }
    provider_sources = provider.sources()
    facts = ProfileFacts(
        cell=cell,
        synthetic=any(source.data_class == "synthetic" for source in provider_sources),
        soil_moisture_source=moisture_source,
        has_soil=soil is not None,
        has_vegetation=vegetation is not None,
        has_wind=wind is not None,
        has_daily=bool(daily),
    )
    body["sources"] = _sources(provider, body)
    body["gaps"] = build_gaps(facts, language)
    return body


class ProfileService:
    """Perfiles en memoria por celda, versión de datos e idioma."""

    def __init__(self, provider: DataProvider):
        self._provider = provider
        self._cache: dict[tuple[str, str | None, str], dict] = {}

    def for_cell(self, cell_id: str, language: str) -> dict:
        key = (cell_id, self._provider.data_version(), language)
        if key not in self._cache:
            self._cache[key] = build_profile(self._provider, cell_id, language)
        return self._cache[key]
