"""Filas tipadas de las vistas de DATA (docs/data_contract.md §3).

Los nombres y unidades son los del contrato: la unidad va en el nombre de la columna.
`None` significa "sin dato"; nunca hay valores de relleno como -999.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Zone:
    zone_id: str
    name: str
    n_cells: int


@dataclass(frozen=True, slots=True)
class Cell:
    """`v_cells`: una celda de 9 km de la malla EASE-Grid 2.0."""

    cell_id: str
    zone_id: str
    zone_name: str
    lat: float
    lon: float
    geometry_wkt: str
    cell_elev_m: float | None
    cell_elev_source: str | None
    power_cell_lat: float
    power_cell_lon: float
    power_elev_m: float
    climate_shared_by_n_cells: int


@dataclass(frozen=True, slots=True)
class ClimatologyDecade:
    """`v_cell_profile`: climatología 2016-2025 de una decena (36 por celda)."""

    cell_id: str
    zone_id: str
    decade: int
    month: int
    frost_prob: float | None
    frost_m2_prob: float | None
    hot_prob_30: float | None
    hot_prob_32: float | None
    hot_prob_35: float | None
    hot_prob_38: float | None
    ws_prob: float | None
    bare_prob: float | None
    heavy_rain_prob: float | None
    windy_prob: float | None
    precip_p10: float | None
    precip_p50: float | None
    precip_p90: float | None
    et0_p50: float | None
    smp_p10: float | None
    smp_p50: float | None
    smp_p90: float | None
    n_years: int
    vulnerable: bool
    vulnerable_reasons: str


@dataclass(frozen=True, slots=True)
class IndicatorDecade:
    """`v_cell_indicators`: indicadores de una celda en un año y una decena."""

    cell_id: str
    zone_id: str
    year: int
    decade: int
    month: int
    n_days: int
    tmax_mean: float | None
    tmin_mean: float | None
    frost_days: int | None
    frost_days_m2: int | None
    hot_days_30: int | None
    hot_days_32: int | None
    hot_days_35: int | None
    hot_days_38: int | None
    precip_mm: float | None
    et0_mm: float | None
    p_minus_et0_mm: float | None
    heavy_rain_days: int | None
    dry_spell_max_d: int | None
    smp_mean: float | None
    ws_days: int | None
    wind_max_ms: float | None
    windy_days: int | None
    ndvi_mean: float | None
    bare_obs: int | None
    precip_src: str | None
    sm_src: str | None
    temp_adj_applied: bool
    complete: bool


@dataclass(frozen=True, slots=True)
class IndicatorYear:
    """`v_cell_year`: totales, medias y máximos anuales de una celda."""

    cell_id: str
    zone_id: str
    year: int
    tmax_mean: float | None
    tmin_mean: float | None
    frost_days: int | None
    frost_days_m2: int | None
    hot_days_30: int | None
    hot_days_32: int | None
    hot_days_35: int | None
    hot_days_38: int | None
    precip_mm: float | None
    et0_mm: float | None
    p_minus_et0_mm: float | None
    heavy_rain_days: int | None
    dry_spell_max_d: int | None
    ws_days: int | None
    wind_max_ms: float | None
    windy_days: int | None
    n_decades_complete: int
    complete_year: bool
    source_flags: str


@dataclass(frozen=True, slots=True)
class SoilLayer:
    """`v_cell_soil`: suelo de una celda a una profundidad (SoilGrids)."""

    cell_id: str
    zone_id: str
    depth_cm: str
    depth_top_cm: int
    depth_bottom_cm: int
    clay_pct: float | None
    clay_pct_p05: float | None
    clay_pct_p95: float | None
    sand_pct: float | None
    sand_pct_p05: float | None
    sand_pct_p95: float | None
    silt_pct: float | None
    silt_pct_p05: float | None
    silt_pct_p95: float | None
    soc_g_kg: float | None
    soc_g_kg_p05: float | None
    soc_g_kg_p95: float | None
    nitrogen_g_kg: float | None
    nitrogen_g_kg_p05: float | None
    nitrogen_g_kg_p95: float | None
    cec_cmol_kg: float | None
    cec_cmol_kg_p05: float | None
    cec_cmol_kg_p95: float | None
    ph: float | None
    ph_p05: float | None
    ph_p95: float | None
    bdod_kg_dm3: float | None
    bdod_kg_dm3_p05: float | None
    bdod_kg_dm3_p95: float | None
    om_pct_est: float | None
    texture_class: str | None
    valid_pixel_pct: float | None
    low_coverage: bool
    # Columnas que DATA añadió en el contrato v2; los datos sintéticos no las traen.
    awc_mm_per_m: float | None = None
    k_factor: float | None = None


@dataclass(frozen=True, slots=True)
class Source:
    """`v_sources`. `data_class` ya viene normalizada a la del contrato de la API:
    `observation`, `model`, `derived`, `estimate` o `synthetic`."""

    source_id: str
    name: str
    organization: str
    product_version: str
    url: str
    resolution: str
    period: str
    access_date: str | None
    license: str
    data_class: str
    status: str
    used_for: str | None


@dataclass(frozen=True, slots=True)
class DailyRow:
    """`v_cell_daily`. Las columnas `*_adj_c` llevan la corrección por altura."""

    cell_id: str
    zone_id: str
    date: str
    tmax_c: float | None
    tmin_c: float | None
    tmean_c: float | None
    tmax_adj_c: float | None
    tmin_adj_c: float | None
    tmean_adj_c: float | None
    temp_adj_applied: bool
    precip_mm: float | None
    rad_mj_m2: float | None
    rh_pct: float | None
    wind_ms: float | None
    wind_max_ms: float | None
    gwetroot_frac: float | None


class DailySeries(tuple):
    """Filas de la serie diaria con su origen: `gold` (vista de DATA), `power_live`
    (respaldo con NASA POWER) o `synthetic` (datos de prueba).

    `elevation_adjusted` es falso si las temperaturas `*_adj_c` no llevan corrección por
    altura porque faltaba alguna elevación.
    """

    origin: str
    elevation_adjusted: bool

    def __new__(cls, rows, origin: str, elevation_adjusted: bool = True):
        series = super().__new__(cls, rows)
        series.origin = origin
        series.elevation_adjusted = elevation_adjusted
        return series
