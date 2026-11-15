# Mapa de datos de la app — campo del front → vista de gold → cálculo

> **Para:** BE (Magdiel) y DATA. **Objetivo:** saber de dónde sale cada campo que pinta el front y detectar rápido
> qué se rompe si el front cambia sus tipos.
> **Base:** `nasa-farm-front/app/src/api/types.ts` en el commit `837b9fb` (14-nov-2026 23:48 UTC) y
> `docs/guia-de-la-app.md` §3. Datos: `data_version = 2026111507`, contrato `docs/data_contract.md` v2.
> Si `types.ts` cambia después de ese commit, revisar este mapa (en especial las filas ⚠️).

## Cómo leer las tablas

- **Vista / columnas:** de dónde lee BE (siempre `WHERE cell_id = ?`). "—" = no viene del lake.
- **Cálculo:** **gold** = ya viene calculado en la vista; **BE** = BE lo calcula en Python a partir de la vista.
- **Estado:**
  - ✅ **listo**: el dato existe y la unidad coincide.
  - 🔧 **BE calcula**: el insumo existe, falta el cálculo en la API.
  - ⚠️ **ojo**: existe, pero con otra unidad, umbral o forma que el front; BE debe convertir o decidir.
  - ⛔ **sin dato en el MVP**: no hay fuente en el lake; devolver `null` y un `gap`.
  - ➖ **no es de DATA**: lo resuelve BE, SCI o el agricultor.
- Las series diarias son de 1991-2025 (35 años, igual que la guía de la app); los indicadores precalculados de
  gold son de 2016-2025 (10 años). Para los resúmenes de clima del front, usar `v_cell_daily`.
- Unidades: el front pide viento en **km/h** (gold da m/s → × 3.6) y fechas como día del año.

## 1. Terreno del usuario (`Field`)

| Campo del front | Vista / columnas | Cálculo | Estado |
|---|---|---|---|
| `geometry` → celda | `v_cells.geometry_wkt`, `lat`, `lon` | BE: celda que contiene el centroide (o la dominante) | 🔧 |
| `centroid`, `area_ha` | — | BE, desde el polígono | ➖ |
| `admin.state`, `admin.municipality` | — | BE (geocodificación). `zone_id` **no** es municipio: es una región aproximada y hay celdas fuera de Coahuila | ➖ |
| `country` | — | BE. Ojo: el rectángulo incluye celdas de Texas | ➖ |
| Fuera de la malla | `v_cells` sin fila | BE: 404 `OUT_OF_REGION` | 🔧 |

## 2. Clima (`ClimateProfile`)

| Campo del front | Vista / columnas | Cálculo | Estado |
|---|---|---|---|
| `source_id` | `v_sources` (`nasa_power`) | — | ✅ |
| `years` | `v_cell_daily.date` | `[1991, 2025]` | ✅ |
| `elevation_m` | `v_cells.cell_elev_m` | gold | ✅ |
| **frost** `threshold_c` | — | Front: helada ≤ 0 °C; gold: Tmin < 0 °C | ⚠️ BE cuenta sobre `tmin_adj_c` con el operador del front |
| frost `risk_threshold_c` | `v_cell_daily.tmin_adj_c` | Front: **riesgo ≤ +2 °C** (helada a ras de suelo). Gold `frost_days_m2` es **< −2 °C** (helada fuerte): **no son lo mismo** | ⚠️ BE calcula desde la diaria |
| frost `last_spring_frost`, `first_fall_frost` (P10/P50/P90) | `v_cell_daily.tmin_adj_c` | BE: por año, última helada antes del 1-jul y primera después; percentiles entre 35 años | 🔧 |
| frost `frost_free_days`, `share_years_without_frost`, `years_analyzed` | `v_cell_daily` | BE | 🔧 |
| frost `by_month[]` (`prob_any_frost`, `mean_frost_days`, `mean_frost_risk_days`, `record_tmin_c`) | `v_cell_daily.tmin_adj_c` | BE, por mes | 🔧 |
| **rain** `annual_mean_mm`, `annual_p20_mm`, `annual_p80_mm`, `annual_cv`, `trend_mm_per_decade` | `v_cell_daily.precip_mm` | BE: suma anual y estadísticos (35 años). `v_cell_year.precip_mm` solo tiene 10 años | 🔧 |
| rain `rainy_months` (media ≥ 40 mm), `wet_day_p95_mm`, `days_per_year_over_25mm/50mm`, `by_month[]` | `v_cell_daily.precip_mm` | BE | 🔧 |
| **heat** `by_month[].mean_tmax_c/mean_tmin_c/record_tmax_c` | `v_cell_daily.tmax_adj_c`, `tmin_adj_c` | BE | 🔧 |
| heat `mean_days_over_30c/35c/40c` | `v_cell_daily.tmax_adj_c` | BE. Gold tiene umbrales 30/32/35/**38**, no 40 | ⚠️ 40 °C solo desde la diaria |
| heat `mean_gdd_base10`, `annual_gdd_base10` | `v_cell_daily.tmean_adj_c` | BE: Σ(Tmedia − 10), tope 30 °C | 🔧 |
| heat `annual_mean_c`, `trend_c_per_decade`, `hottest_month` | `v_cell_daily` | BE | 🔧 |
| **wind** `annual_max_mean_kmh`, `record_kmh`, `windiest_month`, `by_month[]` | `v_cell_daily.wind_max_ms` (10 m) | BE, × 3.6 | 🔧 |
| wind `return_levels_kmh[]`, `gust_factor_assumed` | `v_cell_daily.wind_max_ms` | BE: Gumbel sobre máximos anuales (35); ráfaga = × 1.4 (supuesto del front) | 🔧 |
| **light** `by_month[].mean_solar_mj_m2_day`, `mean_dli_mol_m2_day`, `annual_mean_dli_mol_m2_day` | `v_cell_daily.rad_mj_m2` | BE: DLI = MJ × 0.48 × 4.57. POWER da la radiación en malla de 1° | 🔧 |
| **risk_calendar[]** (52 semanas: `p_frost`, `p_frost_risk`, `p_heat_35c`, `p_heavy_rain`, `p_dry_week`, `mean_*`) | `v_cell_daily` | BE por **semana**. Gold tiene probabilidades por **decena** en `v_cell_profile` (10 años): se pueden usar como respaldo, pero no tienen la misma forma | ⚠️ |
| risk_calendar `p_hail_proxy` | `v_cell_daily` + `v_cells.cell_elev_m` | BE: proxy de la guía (§3.7). Evidencia baja | 🔧 |

## 3. Suelo (`SoilProfile`)

`v_cell_soil` da 3 capas (`0-5`, `5-15`, `15-30`); el front acepta `layers[]` con `depth_cm: [inicio, fin]`
(usar `depth_top_cm`, `depth_bottom_cm`).

| Campo del front | Vista / columnas | Cálculo | Estado |
|---|---|---|---|
| `source_id` | `v_sources` (`soilgrids`) | — | ✅ |
| `layers[].soc_g_kg`, `ph`, `cec_cmol_kg`, `clay_pct`, `sand_pct`, `silt_pct`, `awc_mm_per_m` | mismas columnas | gold | ✅ |
| `layers[].om_pct` | `om_pct_est` | gold (estimación: carbono × 1.724 ÷ 10) | ✅ (otro nombre) |
| `layers[].n_total_g_kg` | `nitrogen_g_kg` | gold | ✅ (otro nombre) |
| `layers[].bulk_density_g_cm3` | `bdod_kg_dm3` | gold; kg/dm³ = g/cm³, mismo número | ✅ (otro nombre) |
| `texture_class` (uno solo) | `v_cell_soil.texture_class` (uno por capa) | BE elige: capa `0-5` o la más frecuente | ⚠️ |
| `k_factor` (uno solo) | `k_factor` de la capa `0-5` | gold | ✅ |
| `confidence` | `low_coverage`, `valid_pixel_pct`, `_p05`/`_p95` | BE: bajar a `low` si `low_coverage` o si `awc_mm_per_m` < 30 (ver `data_quality.md` §8.3) | 🔧 |
| `lab` | — | Lo captura el agricultor | ➖ |
| Fósforo, potasio, micronutrientes | — | Sin fuente global | ⛔ |

## 4. Terreno (`TerrainProfile`)

| Campo del front | Vista / columnas | Cálculo | Estado |
|---|---|---|---|
| `source_id` | `v_sources` (`copernicus_dem_glo90`; la guía dice SRTM 30 m) | — | ⚠️ corregir la etiqueta en el front |
| `elevation_m.mean/min/max` | `v_cell_terrain.elev_mean_m`, `elev_min_m`, `elev_max_m` | gold | ✅ |
| `slope_pct.mean/p90` | `slope_mean_pct`, `slope_p90_pct` | gold | ✅ |
| `aspect_dominant` (string, no nulo) | `aspect_dominant` | Gold usa `N, NE, E, SE, S, SO, O, NO` y **NULL si la celda es plana** | ⚠️ BE mapea NULL a un texto ("plano") |
| `cold_air_pooling_share` | igual | gold (estimación) | ✅ |

## 5. Agua (`WaterProfile`)

| Campo del front | Vista / columnas | Cálculo | Estado |
|---|---|---|---|
| `et.by_month[].et0_mm` | `v_cell_daily.et0_mm` (o `v_cell_indicators.et0_mm` por `month`) | BE: suma mensual media | 🔧 |
| `et.by_month[].et_mm` (ET real, MODIS MOD16) | — | Sin fuente | ⛔ |
| `water_balance_by_month[].p_minus_et0_mm` | `v_cell_indicators.p_minus_et0_mm` (por `month`) o la diaria | BE agrega por mes | 🔧 |
| `soil_moisture.by_month[].mean_m3_m3` | `v_cell_daily.gwetroot_frac` | **No es m³/m³**: es fracción de saturación 0-1 de un modelo (POWER, ~55 km). SMAP no se integra | ⚠️ BE cambia la etiqueta o devuelve `null` + `gap` |
| `groundwater` (GRACE) | — | Sin fuente | ⛔ |

## 6. Vegetación, uso de suelo y peligros

| Campo del front | Vista / columnas | Cálculo | Estado |
|---|---|---|---|
| `vegetation.ndvi_by_month`, `vigor_trend_per_decade` | `ndvi_mean`, `bare_prob` (vacías) | NDVI fuera del MVP (decisión C1) | ⛔ |
| `vegetation.bare_soil_months` | — | Front/BE: meses que no cubre la rotación declarada | ➖ |
| `land_use` (CDL) | — | Solo EE. UU.; no cubre México | ⛔ |
| `hazards.hail` | `v_cell_daily` + elevación | BE: proxy de evidencia baja | 🔧 |

## 7. Fuentes y vacíos (`sources`, `gaps`)

| Campo del front | Vista / columnas | Cálculo | Estado |
|---|---|---|---|
| `sources[].id/dataset/provider/resolution/period/url` | `v_sources.source_id`, `name`, `organization`, `resolution`, `period`, `url` | BE mapea nombres; mostrar solo `status = 'in_use'` | ✅ |
| `gaps[]` | `v_sources.status = 'not_used'` + `data_contract.md` §4 | BE arma los mensajes | 🔧 |

## 8. Otras pantallas

| Bloque del front | Insumo en gold | Estado |
|---|---|---|
| `GreenhouseReport.wind` | `v_cell_daily.wind_max_ms` (retorno 10/25/50 años) | 🔧 |
| `GreenhouseReport.light` | `v_cell_daily.rad_mj_m2` | 🔧 |
| `GreenhouseReport.temperature.heating_degree_hours_base12` | `v_cell_daily.tmin_adj_c` | 🔧 |
| `GreenhouseReport.temperature.hours_over_35c_outside` | Solo hay datos **diarios**: BE estima horas con un supuesto | ⚠️ |
| `GreenhouseReport.co2` (OCO-2) | No está en el lake | ⛔ (valor de referencia fijo) |
| `FutureClimate` (CMIP6) | No está en el lake (Open-Meteo / NEX-GDDP) | ➖ |
| Motores de aptitud y rotación (`SuitabilityDetail`, `Strategy`) | Insumos: `v_cell_daily`, `v_cell_indicators`, `v_cell_profile`, `v_cell_soil`, `v_cell_terrain` | ➖ (BE + SCI) |
| `Crop` (catálogo), calidad del agua, granizo declarado | — | ➖ (SCI / agricultor) |

## 9. Resumen de los ⚠️ (lo que más fácil se rompe)

1. **Umbral de "riesgo de helada":** el front usa ≤ +2 °C; gold `frost_days_m2` es < −2 °C. Calcular desde la diaria.
2. **Calor > 40 °C:** no hay columna en gold; contar en la diaria.
3. **Calendario de riesgos por semana:** gold tiene decenas; BE agrega la diaria por semana.
4. **Humedad del suelo:** gold da fracción de saturación de modelo, no m³/m³ de SMAP.
5. **Textura y orientación:** el front espera un solo valor no nulo; gold da uno por capa y NULL si es plano.
6. **Etiqueta de terreno:** el front dice SRTM 30 m; el dato es Copernicus DEM GLO-90 (~90 m).
7. **Viento:** gold da m/s y el front espera km/h.
