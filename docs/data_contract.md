# Contrato de datos — Field Shift (gold en Athena)

> **De:** ingeniería de datos (DATA). **Para:** backend (BE) y quien consuma los datos.
> **Versión del contrato:** v1 (14-nov-2026). **Datos publicados:** `data_version = 2026111500`.
> Si algo aquí no coincide con lo que devuelve Athena, manda Athena y avísanos.

## 1. Cómo conectarse

| Qué | Valor |
|---|---|
| Región de los datos (`DATA_REGION`) | `us-west-2` |
| Workgroup de Athena (`ATHENA_WORKGROUP`) | `fieldshift` (límite de 1 GB escaneado por consulta) |
| Base de datos (`ATHENA_DATABASE`) | `fieldshift_gold` |
| Versión vigente (`DATA_VERSION_PARAMETER`) | parámetro SSM `/fieldshift/data_version` (formato `YYYYMMDDHH`, UTC) |
| Permisos | política IAM administrada `fieldshift-gold-read` (solo lectura); ver `docs/data_access.md` |

**Reglas de uso**
- Consultar **solo las vistas `v_*`**. Las tablas de gold y todo silver son internos y pueden cambiar.
- Las vistas ya filtran la versión vigente por dentro y **no exponen `data_version`**. Cada publicación
  recrea las vistas y actualiza el parámetro SSM; para saber si hay datos nuevos, vigilar ese parámetro.
- Consultas parametrizadas; nunca concatenar texto del usuario.
- Si se usa reutilización de resultados de Athena, máximo 60 minutos (Athena no detecta que cambió el dato
  debajo de una vista). Para la carga completa en memoria, lanzar las consultas sin reutilización.

## 2. Convenciones

- **Unidad de análisis:** celda de 9 km de la malla EASE-Grid 2.0 (la de SMAP). `cell_id = E9_r{fila}_c{columna}`.
  Los datos son **zonales, no de parcela**: decir "en tu zona (celda de 9 km)", nunca "tu parcela tiene".
- **Decena:** periodo de 10 días, 36 por año. Decena 1 = 1-10 de enero, 2 = 11-20, 3 = 21-31, etc.
  `month = (decade - 1) / 3 + 1`. La tercera decena de cada mes tiene de 8 a 11 días (`n_days`).
- **Ventana de análisis:** 2016-2025 (10 años completos). Las probabilidades van en pasos de 0.1.
- **Unidad en el nombre de la columna:** `_c` °C, `_mm` milímetros, `_pct` %, `_ms` m/s, `_m` metros,
  `_g_kg`, `_cmol_kg`, `_kg_dm3`, `_frac` fracción 0-1, `_prob` probabilidad 0-1.
- **NULL = sin dato.** Nunca hay `-999` ni `-9999`. Athena puede devolver `NaN` en columnas `double`
  vacías (por ejemplo `ndvi_mean`): tratar `NaN` igual que NULL.
- **Fechas en UTC.** El día de POWER se pide con estándar UTC.
- **Clases de dato:** *observación* (medición satelital), *modelo* (reanálisis), *estimación* (derivado con
  un supuesto, por ejemplo la corrección por altura), *derivado* (cálculo directo, por ejemplo conteos).
- **Umbrales = parámetros de diseño**, no hechos científicos (`config/thresholds.yaml`, los aprueba SCI):
  helada 0 °C, helada fuerte −2 °C, calor 30/32/35/38 °C, lluvia intensa 25 mm, día seco < 1 mm,
  estrés hídrico percentil < 20, viento fuerte 10 m/s, corrección por altura 6.5 °C/km,
  decena vulnerable: probabilidad > percentil 75 de la celda **y** ≥ 0.2.

## 3. Vistas

| Vista | Grano (clave) | Filas | Para qué |
|---|---|---|---|
| `v_cells` | `cell_id` | 136 | Polígono → celda; `OUT_OF_REGION` si no existe |
| `v_cell_profile` | `cell_id, decade` | 4,896 | Perfil agroclimático y decenas vulnerables |
| `v_cell_indicators` | `cell_id, year, decade` | 48,960 | Puntaje por año histórico |
| `v_cell_year` | `cell_id, year` | 1,360 | Series anuales |
| `v_cell_soil` | `cell_id, depth_cm` | 408 | Reglas de pH y textura, salud del suelo |
| `v_cell_daily` | `cell_id, date` | 496,808 | Serie diaria para escenarios y viento |
| `v_sources` | `source_id` | 5 | Atribuciones (`GET /sources`) |

Todas (menos `v_sources`) traen `zone_id`: `coah-sureste`, `coah-laguna`, `coah-norte`, `coah-centro`.

### 3.1 `v_cells`

| Columna | Tipo | Significado | NULL |
|---|---|---|---|
| `cell_id` | varchar | Identificador de la celda | nunca |
| `zone_id`, `zone_name` | varchar | Zona y su nombre ("Sureste", "La Laguna", …) | nunca |
| `lat`, `lon` | double | Centroide (WGS84) | nunca |
| `geometry_wkt` | varchar | Polígono de la celda, WKT `POLYGON((lon lat, …))` en WGS84 | nunca |
| `cell_elev_m` | double | Elevación media de la celda (m) | si no hay DEM |
| `cell_elev_source` | varchar | `copernicus_dem_glo90` | si no hay DEM |
| `power_cell_lat`, `power_cell_lon` | double | Centro del cuadro de POWER (0.5° × 0.625°) que da el clima | nunca |
| `power_elev_m` | double | Elevación media de ese cuadro según POWER (m) | nunca |
| `climate_shared_by_n_cells` | bigint | Cuántas celdas comparten esa misma serie de clima | nunca |

### 3.2 `v_cell_profile` (climatología 2016-2025, 36 filas por celda)

| Columna | Tipo | Significado |
|---|---|---|
| `cell_id`, `zone_id`, `decade`, `month` | | Clave y mes (1-12) |
| `frost_prob`, `frost_m2_prob` | double | Fracción de años con ≥ 1 día de Tmin < 0 °C / < −2 °C en la decena |
| `hot_prob_30`, `hot_prob_32`, `hot_prob_35`, `hot_prob_38` | double | Fracción de años con ≥ 1 día de Tmax sobre ese umbral |
| `heavy_rain_prob` | double | Fracción de años con ≥ 1 día de lluvia > 25 mm |
| `ws_prob` | double | Fracción de años con ≥ 1 día de estrés hídrico (percentil de humedad < 20) |
| `windy_prob` | double | Fracción de años con ≥ 1 día de viento máximo > 10 m/s |
| `bare_prob` | double | Suelo descubierto (NDVI < 0.25). **Vacío hasta integrar NDVI** |
| `precip_p10`, `precip_p50`, `precip_p90` | double | Percentiles entre años de la lluvia de la decena (mm) |
| `et0_p50` | double | Mediana de la ET0 de la decena (mm) |
| `smp_p10`, `smp_p50`, `smp_p90` | double | Percentiles entre años del percentil medio de humedad (0-100) |
| `n_years` | bigint | Años completos usados (normalmente 10) |
| `vulnerable` | boolean | La decena es vulnerable por al menos un motivo |
| `vulnerable_reasons` | varchar | Motivos separados por coma: `frost`, `heat` (umbral 35 °C), `water_stress`, `heavy_rain`; cadena vacía si no hay |

### 3.3 `v_cell_indicators` (celda × año × decena)

| Columna | Tipo | Significado |
|---|---|---|
| `cell_id`, `zone_id`, `year`, `decade`, `month`, `n_days` | | Clave, mes y días de la decena |
| `tmax_mean`, `tmin_mean` | double | Medias de Tmax y Tmin **ajustadas por altura** (°C) |
| `frost_days`, `frost_days_m2` | bigint | Días con Tmin ajustada < 0 °C / < −2 °C |
| `hot_days_30`, `hot_days_32`, `hot_days_35`, `hot_days_38` | bigint | Días con Tmax ajustada sobre el umbral. El motor usa el más cercano a la T crítica del cultivo |
| `precip_mm` | double | Lluvia total de la decena |
| `et0_mm` | double | ET de referencia, Hargreaves-Samani (FAO-56), total de la decena |
| `p_minus_et0_mm` | double | Lluvia − ET0 (balance hídrico simple) |
| `heavy_rain_days` | bigint | Días con lluvia > 25 mm |
| `dry_spell_max_d` | bigint | Racha seca más larga que **termina** en la decena; la racha cruza decenas y años |
| `smp_mean` | double | Percentil medio de humedad de raíz (0-100) respecto a la misma celda y decena |
| `ws_days` | bigint | Días con percentil de humedad < 20 |
| `wind_max_ms` | double | Viento máximo a 10 m en la decena |
| `windy_days` | bigint | Días con viento máximo > 10 m/s |
| `ndvi_mean`, `bare_obs` | double, bigint | **Vacíos hasta integrar NDVI** |
| `precip_src` | varchar | `power` |
| `sm_src` | varchar | `power_gwetroot` (humedad de modelo); pasará a `smap_l4` cuando se integre SMAP |
| `temp_adj_applied` | boolean | `true` si se aplicó la corrección por altura |
| `complete` | boolean | `false` si más del 30 % de los días de la decena no tenían dato |

### 3.4 `v_cell_year` (celda × año)

`tmax_mean`, `tmin_mean` (medias anuales ajustadas), totales anuales de `frost_days`, `frost_days_m2`,
`hot_days_30/32/35/38`, `precip_mm`, `et0_mm`, `p_minus_et0_mm`, `heavy_rain_days`, `ws_days`, `windy_days`;
máximos anuales `dry_spell_max_d` y `wind_max_ms`; `n_decades_complete` (0-36), `complete_year` (boolean) y
`source_flags` (texto, por ejemplo `precip=power;sm=power_gwetroot;temp=elevation_adjusted`).

### 3.5 `v_cell_soil` (celda × profundidad)

`depth_cm` ∈ {`0-5`, `5-15`, `15-30`}; `depth_top_cm`, `depth_bottom_cm` (enteros, para ordenar).

| Columna | Unidad | Significado |
|---|---|---|
| `clay_pct`, `sand_pct`, `silt_pct` | % | Textura (suman ~100) |
| `ph` | pH | pH en agua |
| `soc_g_kg` | g/kg | Carbono orgánico |
| `om_pct_est` | % | Materia orgánica **estimada** = carbono × 1.724 ÷ 10 |
| `nitrogen_g_kg` | g/kg | Nitrógeno total |
| `cec_cmol_kg` | cmol(c)/kg | Capacidad de intercambio catiónico |
| `bdod_kg_dm3` | kg/dm³ | Densidad aparente |
| `<variable>_p05`, `<variable>_p95` | igual | Media en la celda de las capas Q0.05 y Q0.95 de SoilGrids: **incertidumbre del modelo**, no variación dentro de la celda |
| `texture_class` | texto | Clase textural USDA en inglés (`loam`, `clay loam`, `sandy clay loam`, `sandy loam`, `clay`, …) |
| `valid_pixel_pct` | % | Píxeles de 250 m con dato dentro de la celda |
| `low_coverage` | boolean | `true` si `valid_pixel_pct` < 80 (zonas urbanas o agua enmascaradas) |

### 3.6 `v_cell_daily` (celda × día, 2016-2025)

`date` (date, UTC); `tmax_c`, `tmin_c`, `tmean_c` (POWER crudo); `tmax_adj_c`, `tmin_adj_c`, `tmean_adj_c`
(ajustadas por altura; son las que usan los indicadores); `temp_adj_applied`; `precip_mm`; `rad_mj_m2`
(MJ/m²/día); `rh_pct`; `wind_ms` (2 m); `wind_max_ms` (10 m); `gwetroot_frac` (humedad de raíz de modelo, 0-1).
Para un escenario "+2 °C" basta sumar a las columnas `*_adj_c` y volver a contar con los umbrales de §2.
Tamaño: ~3,650 filas por celda; consultar por `cell_id`.

### 3.7 `v_sources`

`source_id`, `name`, `organization`, `product_version`, `url`, `resolution`, `period`, `access_date`,
`license`, `data_class`, `status` (`in_use` | `pending`), `used_for`.
Hoy: `nasa_power`, `soilgrids`, `copernicus_dem_glo90` en uso; `smap_l4` y `modis_ndvi` pendientes.

## 4. Limitaciones que la interfaz debe declarar

1. **Resolución:** indicadores por celda de 9 km. El clima viene de cuadros de ~55 km (POWER) compartidos
   por varias celdas (`climate_shared_by_n_cells`); solo la temperatura se diferencia por celda, mediante
   la corrección por altura, que es una **estimación** (6.5 °C/km fijo).
2. **Lluvia, viento, radiación y humedad** son idénticos para todas las celdas de un mismo cuadro POWER.
3. **Humedad del suelo:** por ahora de modelo (POWER GWETROOT), expresada como percentil. Con SMAP cambiará
   `sm_src` y los valores de `smp_*` y `ws_*`.
4. **Suelo descubierto (NDVI):** aún sin datos.
5. **Ventana de 10 años:** una probabilidad de 0.1 significa "ocurrió 1 de 10 años".
6. **Suelo:** SoilGrids es una estimación global a 250 m; sin fósforo, potasio ni micronutrientes.
   Recomendar análisis de laboratorio.
7. **Elevación:** Copernicus DEM GLO-90 (ESA), no NASA.
8. Sin granizo ni calidad del agua: son preguntas al agricultor.

## 5. Qué cambia y qué rompe el contrato

- **No rompe:** agregar columnas o vistas; publicar una versión nueva; que `sm_src` pase a `smap_l4`;
  que `ndvi_mean`, `bare_obs` y `bare_prob` empiecen a traer valores.
- **Rompe (se avisa antes):** renombrar o quitar una columna o vista, cambiar una unidad o un tipo.
- **Próximas publicaciones previstas:** + SMAP (humedad), + NDVI (suelo descubierto).

## 6. Ejemplos

Consultas listas en `athena/queries/`. Muestra real de dos celdas en `docs/data_sample/`.
