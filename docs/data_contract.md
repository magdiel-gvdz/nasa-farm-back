# Contrato de datos — Field Shift (gold en Athena)

> **De:** ingeniería de datos (DATA). **Para:** backend (BE) y quien consuma los datos.
> **Versión del contrato:** v2 (15-nov-2026, Coahuila completo). **Datos publicados:** `data_version = 2026111507`.
> Cambios desde v1.1 (**no rompen nada**: mismas vistas, columnas, tipos y unidades): cobertura de **todo
> Coahuila** (136 → **2,992 celdas**, 4 → **5 regiones**, se suma `coah-carbonifera`); las 136 celdas anteriores
> conservan su `cell_id` e indicadores idénticos. SMAP y NDVI siguen fuera del MVP.
> Historia: v1.1 (`2026111501`) sumó `v_cell_daily` 1991-2025 + `et0_mm`, `v_cell_terrain` y agua/K en `v_cell_soil`.
> Si algo aquí no coincide con lo que devuelve Athena, manda Athena y avísanos.

## 1. Cómo conectarse

| Qué | Valor |
|---|---|
| Región de los datos (`DATA_REGION`) | `us-west-2` |
| Workgroup de Athena (`ATHENA_WORKGROUP`) | `fieldshift` (límite de 1 GB escaneado por consulta) |
| Base de datos (`ATHENA_DATABASE`) | `fieldshift_gold` |
| Versión vigente (`DATA_VERSION_PARAMETER`) | parámetro SSM `/fieldshift/data_version` (formato `YYYYMMDDHH`, UTC) |
| Permisos | política IAM administrada `fieldshift-gold-read` (solo lectura); ver `docs/data_access.md` |

**La API vive en us-east-1 y los datos en us-west-2.** Los clientes de Athena y SSM se crean con la región de
los datos explícita; si se omite, boto3 usa la región de la Lambda y no encuentra el workgroup ni el parámetro:

```python
athena = boto3.client("athena", region_name="us-west-2")
ssm = boto3.client("ssm", region_name="us-west-2")
```

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
- **Ventana de análisis:** 2016-2025 (10 años completos) para `v_cell_profile`, `v_cell_indicators` y
  `v_cell_year`; las probabilidades van en pasos de 0.1. `v_cell_daily` trae la serie completa **1991-2025**
  (35 años) para que BE calcule percentiles largos (fechas de helada P10/P90, viento de 50 años).
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
| `v_cells` | `cell_id` | 2,992 | Polígono → celda; `OUT_OF_REGION` si no existe |
| `v_cell_profile` | `cell_id, decade` | 107,712 | Perfil agroclimático y decenas vulnerables |
| `v_cell_indicators` | `cell_id, year, decade` | 1,077,120 | Puntaje por año histórico |
| `v_cell_year` | `cell_id, year` | 29,920 | Series anuales |
| `v_cell_soil` | `cell_id, depth_cm` | 8,976 | Reglas de pH y textura, salud del suelo |
| `v_cell_daily` | `cell_id, date` | 38,249,728 | Serie diaria 1991-2025 para escenarios, heladas, viento y demanda de agua |
| `v_cell_terrain` | `cell_id` | 2,992 | Elevación, pendiente, orientación y bajíos fríos |
| `v_sources` | `source_id` | 5 | Atribuciones (`GET /sources`) |

Todas (menos `v_sources`) traen `zone_id`. **Siempre filtrar por `cell_id`**: ninguna vista está pensada para
leerse completa desde la API (`v_cell_daily` completa son 38 millones de filas).

**Cobertura y regiones.** La malla cubre el **rectángulo que encierra a Coahuila** (lon −103.967 a −99.85,
lat 24.55 a 29.884; extremos de los 38 municipios, INEGI), sin recortar al contorno del estado. Por eso incluye
celdas de **Nuevo León, Tamaulipas, Chihuahua, Durango, Zacatecas y Texas (EE. UU.)**: tienen datos completos y
válidos, pero no son Coahuila. No hay columna que las marque; la app ubica la parcela por celda y no necesita
distinguirlas. Las 5 regiones son **rectángulos aproximados** (no límites municipales); cada celda está en una
sola región (la que contiene su centroide o, fuera de todas, la más cercana):

| `zone_id` | `zone_name` | Celdas | Municipios de referencia |
|---|---|---|---|
| `coah-sureste` | Sureste | 621 | Saltillo, Arteaga, Ramos Arizpe, General Cepeda, Parras |
| `coah-laguna` | La Laguna | 391 | Torreón, Matamoros, Francisco I. Madero, San Pedro, Viesca |
| `coah-centro` | Centro-Desierto | 1,260 | Cuatro Ciénegas, San Buenaventura, Frontera, Monclova, Ocampo, Sierra Mojada |
| `coah-carbonifera` | Carbonífera | 336 | Sabinas, Múzquiz, San Juan de Sabinas, Progreso |
| `coah-norte` | Norte (Cinco Manantiales) | 384 | Piedras Negras, Allende, Nava, Morelos, Zaragoza, Acuña |

Una celda de 9 km puede cruzar el límite entre regiones: `zone_id` es una etiqueta para agrupar, no un dato
administrativo.

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
| `bare_prob` | double | Suelo descubierto (NDVI < 0.25). **Vacío: NDVI no se integra en el MVP** |
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
| `ndvi_mean`, `bare_obs` | double, bigint | **Vacíos: NDVI no se integra en el MVP** |
| `precip_src` | varchar | `power` |
| `sm_src` | varchar | `power_gwetroot` (humedad de modelo); SMAP no se integra en el MVP |
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
| `wv0033_m3m3` | m³/m³ | Agua retenida a −33 kPa (capacidad de campo) |
| `wv1500_m3m3` | m³/m³ | Agua retenida a −1500 kPa (punto de marchitez permanente) |
| `awc_mm_per_m` | mm/m | Agua disponible para la planta = (`wv0033` − `wv1500`) × 1000. Para mm en 0-30 cm: Σ `awc_mm_per_m` × espesor (m). Incertidumbre alta: orden de magnitud zonal (ver `data_quality.md` §7) |
| `k_factor` | t·ha·h/(ha·MJ·mm) | Erosionabilidad USLE **estimada** (EPIC, Williams 1995) con arena, limo, arcilla y carbono. Para erosión usar la capa `0-5`. Típico 0.01-0.07 |
| `<variable>_p05`, `<variable>_p95` | igual | Media en la celda de las capas Q0.05 y Q0.95 de SoilGrids: **incertidumbre del modelo**, no variación dentro de la celda |
| `texture_class` | texto | Clase textural USDA en inglés (`loam`, `clay loam`, `sandy clay loam`, `sandy loam`, `clay`, …) |
| `valid_pixel_pct` | % | Píxeles de 250 m con dato dentro de la celda |
| `low_coverage` | boolean | `true` si `valid_pixel_pct` < 80 (zonas urbanas o agua enmascaradas) |

### 3.6 `v_cell_daily` (celda × día, 1991-2025)

`date` (date, UTC); `tmax_c`, `tmin_c`, `tmean_c` (POWER crudo); `tmax_adj_c`, `tmin_adj_c`, `tmean_adj_c`
(ajustadas por altura; son las que usan los indicadores); `temp_adj_applied`; `precip_mm`; `rad_mj_m2`
(MJ/m²/día); `rh_pct`; `wind_ms` (2 m); `wind_max_ms` (10 m); `gwetroot_frac` (humedad de raíz de modelo, 0-1);
`et0_mm` (ET de referencia diaria, Hargreaves-Samani FAO-56 con las temperaturas ajustadas y la latitud de la
celda; demanda de un cultivo ≈ Σ `et0_mm` × Kc). En 2016-2025, la suma de `et0_mm` por decena coincide con
`v_cell_indicators.et0_mm`.
Para un escenario "+2 °C" basta sumar a las columnas `*_adj_c` y volver a contar con los umbrales de §2.
Tamaño: 12,784 filas por celda (~15 MB escaneados por consulta de una celda; la vista completa tiene
38,249,728 filas); consultar siempre por `cell_id`.

### 3.6b `v_cell_terrain` (una fila por celda)

Copernicus DEM GLO-90 (~90 m, ~10,500 píxeles por celda). Datos de terreno = *observación*; pendiente,
orientación y bajío frío = *derivado/estimación* con parámetros de diseño (`config/thresholds.yaml`, bloque `terrain`).

| Columna | Unidad | Significado |
|---|---|---|
| `elev_mean_m`, `elev_min_m`, `elev_max_m`, `elev_std_m` | m | Elevación media, mínima, máxima y desviación dentro de la celda (`elev_mean_m` = `v_cells.cell_elev_m`) |
| `slope_mean_pct`, `slope_p90_pct` | % | Pendiente media y percentil 90 (100 % = 45°) |
| `aspect_dominant` | texto | Orientación más frecuente hacia donde mira la ladera: `N`, `NE`, `E`, `SE`, `S`, `SO`, `O`, `NO`, entre píxeles con pendiente > 2 %. NULL = celda plana |
| `aspect_dominant_share` | 0-1 | Fracción de esos píxeles con la orientación dominante (bajo = orientaciones mezcladas) |
| `cold_air_pooling_share` | 0-1 | **Estimación** de la fracción de la celda en hondonada donde se acumula aire frío: píxeles > 15 m por debajo de la media de ~1 km y con pendiente < 3 %. Indica dónde la helada puede ser más fuerte que la de la celda |
| `n_pixels` | | Píxeles del DEM en la celda |

### 3.7 `v_sources`

`source_id`, `name`, `organization`, `product_version`, `url`, `resolution`, `period`, `access_date`,
`license`, `data_class`, `status` (`in_use` | `pending` | `not_used`), `used_for`.
Hoy: `nasa_power`, `soilgrids`, `copernicus_dem_glo90` en uso; `smap_l4` y `modis_ndvi` en `not_used`
(SMAP y NDVI no se integran en el MVP; la interfaz no debe presentarlos como fuentes activas).
Nota: `nasa_power.period` dice la ventana de indicadores (2016-2025); la serie diaria cubre 1991-2025.

## 4. Limitaciones que la interfaz debe declarar

1. **Resolución:** indicadores por celda de 9 km. El clima viene de cuadros de ~55 km (POWER) compartidos
   por varias celdas (`climate_shared_by_n_cells`); solo la temperatura se diferencia por celda, mediante
   la corrección por altura, que es una **estimación** (6.5 °C/km fijo).
2. **Lluvia, viento, radiación y humedad** son idénticos para todas las celdas de un mismo cuadro POWER.
3. **Humedad del suelo:** de modelo (POWER GWETROOT, ~55 km), expresada como percentil. SMAP no se integra
   en el MVP.
4. **Suelo descubierto (NDVI):** sin datos; NDVI no se integra en el MVP.
5. **Ventana de 10 años:** una probabilidad de 0.1 significa "ocurrió 1 de 10 años".
6. **Suelo:** SoilGrids es una estimación global a 250 m; sin fósforo, potasio ni micronutrientes.
   Recomendar análisis de laboratorio.
7. **Elevación y terreno:** Copernicus DEM GLO-90 (ESA), no NASA. Es un modelo de superficie (incluye
   edificios y árboles). Bajío frío y orientación son estimaciones topográficas, no mediciones de temperatura.
8. **Agua disponible y factor K:** derivados de SoilGrids (estimación global a 250 m) con una fórmula empírica;
   sirven para comparar zonas, no sustituyen una curva de retención ni una medición de erosión.
9. **Racha seca:** en `v_cell_indicators` cuenta desde el 1-ene-2016 (inicio de la ventana); la de la
   primera decena de 2016 puede quedar corta. Con `v_cell_daily` se puede calcular con la historia completa.
10. Sin granizo ni calidad del agua: son preguntas al agricultor.
11. **Celdas fuera de Coahuila:** el rectángulo incluye partes de estados vecinos y de Texas (§3). Sus datos son
    válidos, pero la etiqueta `zone_id` (región de Coahuila) es solo la región más cercana.
12. **Agua disponible muy baja en 32 celdas** (sobre todo Carbonífera, 15-30 cm): SoilGrids da capacidad de campo
    casi igual al punto de marchitez y `awc_mm_per_m` queda < 30 mm/m. Es de la fuente; ver `data_quality.md` §8.

## 5. Qué cambia y qué rompe el contrato

- **No rompe:** agregar columnas o vistas; publicar una versión nueva; que `sm_src` pase a `smap_l4` o
  que `ndvi_mean`, `bare_obs` y `bare_prob` traigan valores en el futuro (hoy no está previsto).
- **Rompe (se avisa antes):** renombrar o quitar una columna o vista, cambiar una unidad o un tipo.
- **Próximas publicaciones previstas:** ninguna antes de la demo. SMAP y NDVI quedan fuera del MVP.
- **Al cambiar de versión:** los datos de suelo de una celda pueden variar levemente entre versiones si cambia el
  procesamiento (ver `data_quality.md` §8); los indicadores climáticos de `2026111501` y `2026111507` son idénticos
  en las 136 celdas comunes. Las cachés deben llevar `data_version` en la clave.

## 6. Ejemplos

Consultas listas en `athena/queries/` (01-06 para la API; 10-14 son validaciones de DATA). Qué campo del front
sale de qué vista y qué calcula BE: `docs/app_data_map.md`. Muestra real de dos celdas en `docs/data_sample/` (incluye `v_cell_terrain`;
`v_cell_daily` solo 2025 para que pese poco).
