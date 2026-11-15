"""Perfil agroclimático de la zona (celda de 9 km) de una geocerca.

Las secciones sin dato en el MVP son `null` y se nombran en `gaps`.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator

from app.api.schemas.common import (
    Confidence,
    Gap,
    Month,
    MonthDay,
    Probability,
    ResponseModel,
    Source,
    check_months,
)


class Monthly(ResponseModel):
    month: Month


class FrostDate(ResponseModel):
    doy: int = Field(ge=1, le=366)
    date: MonthDay


class FrostDates(ResponseModel):
    p10: FrostDate
    p50: FrostDate
    p90: FrostDate


class FrostFreeDays(ResponseModel):
    p10: int
    p50: int


class FrostMonth(Monthly):
    prob_any_frost: Probability
    mean_frost_days: float | None
    mean_severe_frost_days: float | None
    record_tmin_c: float | None


class Frost(ResponseModel):
    threshold_c: float
    severe_threshold_c: float
    years_analyzed: int
    last_spring_frost: FrostDates | None
    first_fall_frost: FrostDates | None
    frost_free_days: FrostFreeDays | None
    share_years_without_frost: Probability | None
    by_month: list[FrostMonth]

    _months = field_validator("by_month")(check_months)


class RainMonth(Monthly):
    mean_mm: float
    p20_mm: float | None
    p80_mm: float | None
    mean_heavy_rain_days: float | None


class Rain(ResponseModel):
    source_id: str
    annual_mean_mm: float
    annual_p20_mm: float | None
    annual_p80_mm: float | None
    annual_cv: float | None
    trend_mm_per_decade: float | None = Field(description="Tendencia por cada 10 años")
    rainy_months: list[Month]
    heavy_rain_threshold_mm: float
    by_month: list[RainMonth]

    _months = field_validator("by_month")(check_months)


class HeatMonth(Monthly):
    mean_tmax_c: float
    mean_tmin_c: float
    record_tmax_c: float | None
    mean_gdd_base10: float | None
    mean_days_over_30c: float | None
    mean_days_over_32c: float | None = None
    mean_days_over_35c: float | None
    mean_days_over_38c: float | None


class Heat(ResponseModel):
    thresholds_c: list[float] = Field(description="Umbrales de Tmax con los que se cuentan días")
    annual_mean_c: float
    trend_c_per_decade: float | None = Field(description="Tendencia por cada 10 años")
    hottest_month: Month
    annual_gdd_base10: float | None
    by_month: list[HeatMonth]

    _months = field_validator("by_month")(check_months)


class WindReturnLevel(ResponseModel):
    return_period_years: int
    sustained_kmh: float
    estimated_gust_kmh: float


class WindMonth(Monthly):
    mean_daily_max_kmh: float
    record_kmh: float | None


class Wind(ResponseModel):
    annual_max_mean_kmh: float
    record_kmh: float | None
    windiest_month: Month
    gust_factor_assumed: float
    return_levels_kmh: list[WindReturnLevel]
    by_month: list[WindMonth]

    _months = field_validator("by_month")(check_months)


class LightMonth(Monthly):
    mean_solar_mj_m2_day: float
    mean_dli_mol_m2_day: float


class Light(ResponseModel):
    annual_mean_dli_mol_m2_day: float
    by_month: list[LightMonth]

    _months = field_validator("by_month")(check_months)


class RiskDecade(ResponseModel):
    """Una decena del año: días 1-10, 11-20 y 21 a fin de cada mes."""

    decade: int = Field(ge=1, le=36)
    month: Month
    starts: MonthDay
    p_frost: Probability | None
    p_frost_severe: Probability | None
    p_heat_30c: Probability | None = None
    p_heat_32c: Probability | None = None
    p_heat_35c: Probability | None
    p_heat_38c: Probability | None = None
    p_heavy_rain: Probability | None
    p_water_stress: Probability | None
    p_bare_soil: Probability | None
    p_strong_wind: Probability | None = None
    precip_p50_mm: float | None
    et0_p50_mm: float | None
    vulnerable: bool
    vulnerable_reasons: list[str]


class Climate(ResponseModel):
    source_id: str
    years: tuple[int, int]
    elevation_m: float | None
    frost: Frost
    rain: Rain
    heat: Heat
    wind: Wind | None
    light: Light | None
    risk_calendar: list[RiskDecade]

    @field_validator("risk_calendar")
    @classmethod
    def thirty_six_decades(cls, entries: list[RiskDecade]) -> list[RiskDecade]:
        if [entry.decade for entry in entries] != list(range(1, 37)):
            raise ValueError("risk_calendar debe tener las decenas 1 a 36, una vez cada una")
        return entries


class UncertaintyRange(ResponseModel):
    """Capas Q0.05 y Q0.95 de SoilGrids: incertidumbre del modelo, no variación en la celda."""

    p05: float
    p95: float


class SoilLayer(ResponseModel):
    depth_cm: tuple[int, int]
    soc_g_kg: float | None
    om_pct: float | None
    n_total_g_kg: float | None
    ph: float | None
    cec_cmol_kg: float | None
    clay_pct: float | None
    sand_pct: float | None
    silt_pct: float | None
    bulk_density_g_cm3: float | None
    awc_mm_per_m: float | None
    uncertainty: dict[str, UncertaintyRange] = Field(
        default_factory=dict, description="Rango P05-P95 por propiedad"
    )


class Soil(ResponseModel):
    source_id: str
    confidence: Confidence
    texture_class: str | None
    layers: list[SoilLayer]
    lab: dict[str, Any] | None = Field(description="Valores del análisis de laboratorio")
    k_factor: float | None


class Elevation(ResponseModel):
    mean: float
    min: float | None
    max: float | None


class Slope(ResponseModel):
    mean: float
    p90: float


class Terrain(ResponseModel):
    source_id: str
    elevation_m: Elevation
    slope_pct: Slope | None
    aspect_dominant: str | None
    cold_air_pooling_share: Probability | None


class SoilMoistureMonth(Monthly):
    mean_m3_m3: float | None
    # Percentil (0-100) de la humedad respecto a la misma celda y época del año.
    percentile_p10: float | None = None
    percentile_p50: float | None = None
    percentile_p90: float | None = None


class SoilMoisture(ResponseModel):
    source_id: str
    years: tuple[int, int]
    by_month: list[SoilMoistureMonth]

    _months = field_validator("by_month")(check_months)


class EvapotranspirationMonth(Monthly):
    et_mm: float | None
    et0_mm: float


class Evapotranspiration(ResponseModel):
    source_id: str
    method: str
    by_month: list[EvapotranspirationMonth]

    _months = field_validator("by_month")(check_months)


class WaterBalanceMonth(Monthly):
    p_minus_et0_mm: float


class Groundwater(ResponseModel):
    source_id: str
    trend_cm_per_year: float
    years: tuple[int, int]


class Water(ResponseModel):
    soil_moisture: SoilMoisture | None
    et: Evapotranspiration | None
    water_balance_by_month: list[WaterBalanceMonth]
    groundwater: Groundwater | None

    _months = field_validator("water_balance_by_month")(check_months)


class NdviMonth(Monthly):
    mean: float
    p10: float | None
    p90: float | None


class Vegetation(ResponseModel):
    source_id: str
    ndvi_by_month: list[NdviMonth]
    bare_soil_months: list[Month]
    bare_soil_decades: list[int]
    vigor_trend_per_decade: float | None = Field(description="Tendencia por cada 10 años")

    _months = field_validator("ndvi_by_month")(check_months)


class LandUseYear(ResponseModel):
    year: int
    crop: str
    share: Probability


class LandUse(ResponseModel):
    source_id: str
    history: list[LandUseYear]
    detected_rotation: list[str]


class Hail(ResponseModel):
    source_id: str
    level: Literal["low", "medium", "high"]
    evidence: Confidence
    months_of_concern: list[Month]
    note: str


class Hazards(ResponseModel):
    hail: Hail | None


class FieldProfile(ResponseModel):
    status: Literal["ready"]
    field_id: str
    cell_id: str
    zone_id: str
    resolution_m: int = Field(description="Lado de la celda de análisis; el dato es zonal")
    computed_at: datetime
    pipeline_version: str
    data_version: str = Field(description="Versión de los datos de DATA con la que se calculó")
    climate: Climate
    soil: Soil | None
    terrain: Terrain | None
    water: Water
    vegetation: Vegetation | None
    land_use: LandUse | None
    hazards: Hazards
    sources: list[Source]
    gaps: list[Gap]
