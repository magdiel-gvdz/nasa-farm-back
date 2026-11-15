# Field Shift / RotaSat — Arquitectura y concepto de datos

> **Actualización (14-nov-2026, DATA):** el contrato vigente de las vistas está en
> [`data_contract.md`](data_contract.md); cómo conectarse, en [`data_access.md`](data_access.md); la
> infraestructura real, en [`data_infra.md`](data_infra.md); la calidad, en [`data_quality.md`](data_quality.md).
> Cambios respecto a este documento: la pila se despliega con Terraform (no CloudFormation); la elevación
> sale de Copernicus DEM GLO-90 (no de SRTM por AppEEARS); hay una séptima vista, `v_cell_daily`;
> gold V0 usa la humedad de POWER hasta integrar SMAP, y NDVI sigue pendiente.

> **Para:** Solution Architect del equipo. **De:** Ingeniería de datos.
> **Fecha:** sáb 14-nov-2026 (NASA Space Apps 2026, hackathon del 14 al 15 de nov; H0 = sáb 09:00, hora de Monterrey).
> **Propósito:** documento autocontenido para validar la propuesta de datos y continuar el trabajo. No requiere ningún otro archivo del repositorio.
> **Cómo leerlo:** §1-2 contexto · §3 arquitectura · §4-6 fuentes y malla · §7-9 modelo de datos (raw, silver, gold, vistas) · §10 decisiones · §11 costos y riesgos · §12 estado · §13 qué validar.

---

## 1. Contexto del producto

**Reto NASA:** *"Field Shift: Adapting Farms with NASA Data"*. Herramienta de apoyo a decisiones que combina observaciones de la NASA con información local de suelo, características de cultivos y prioridades del agricultor para **explorar rotaciones de cultivo** que mejoren la salud del suelo y la resiliencia al clima y al agua.

**Producto (RotaSat):** el agricultor marca su terreno en un mapa, indica su rotación actual y sus prioridades. La app muestra el perfil agroclimático histórico de su zona y **compara 3 rotaciones** (la actual + 2 alternativas) con puntaje, desglose, razones, evidencia, vacíos de información y riesgos a revisar con un agrónomo.

**Principios que afectan al diseño de datos**
- **Explicable:** motor de reglas + puntaje multicriterio. Sin machine learning ni IA generativa.
- **Honestidad de resolución:** los datos son **zonales (celda de 9 km)**, no de parcela. Nunca "tu parcela tiene X"; siempre "en tu zona (celda de 9 km)...".
- **Trazabilidad:** cada cifra lleva fuente, resolución y clase de dato (observación NASA, modelo, derivado, estimación).
- **Umbrales = parámetros de diseño** en configuración, no hechos científicos.

**Equipo (roles):** TL (arquitectura de la app y despliegue), BE (API y motor), FE (frontend), **DATA (ingeniería de datos)**, SCI (rol científico: catálogo de cultivos, reglas agronómicas, definición y aprobación de umbrales e indicadores).

**Alcance de DATA:** termina cuando **gold está publicado y consultable en Athena con un contrato documentado**. API, motor, frontend y su infraestructura son de otros roles.

---

## 2. Región piloto

4 zonas de Coahuila, México. Celdas = celdas de 9 km cuyo **centroide** cae dentro del bbox.

| zone_id | Zona | Municipios | Rasgo | bbox (lon_min, lat_min, lon_max, lat_max) | Celdas |
|---|---|---|---|---|---|
| `coah-sureste` | Sureste | Saltillo, Arteaga, General Cepeda | Alta, semiárida, heladas | -101.6, 25.2, -100.7, 25.6 | 45 |
| `coah-laguna` | La Laguna | Torreón, Matamoros, Fco. I. Madero, San Pedro | Calor extremo, forrajes, acuífero presionado | -103.5, 25.45, -102.9, 25.85 | 35 |
| `coah-norte` | Norte (Cinco Manantiales) | Allende, Nava, Morelos, Zaragoza | Baja, cálida, más lluvia | -101.0, 28.15, -100.6, 28.55 | 20 |
| `coah-centro` | Centro-Desierto | Cuatro Ciénegas, San Buenaventura, Frontera | Muy seca, conflicto por agua | -102.2, 26.85, -101.4, 27.15 | 36 |
| **Total** | | | | | **136** |

El pipeline recibe una **lista de zonas** desde configuración (`config/zones.yaml`); agregar una zona = agregar una entrada y volver a correr. Hasta ~500 celdas la arquitectura no cambia (ver §11).

---

## 3. Arquitectura de datos (AWS us-west-2)

```
                 ┌──────────── EXTRACCIÓN: Lambda (contenedor arm64, Python 3.12) ────────────┐
 invocación      │ ingest_power     → NASA POWER API (sin cuenta)                              │
 manual / cada   │ ingest_soil      → SoilGrids WCS → recorte + media zonal por celda          │──► S3 lake  raw/
 15 min (poll)   │ appeears_submit  → AppEEARS: SMAP + SRTM (puntos), NDVI (área)  [una vez]   │
                 │ appeears_poll    → si la tarea terminó, descarga CSV / NetCDF y aplana       │
                 └─────────────────────────────────────────────────────────────────────────────┘
                                                  │
                         Glue Python shell 3.9 (pandas + awswrangler), 2 jobs:
                         silver_build (--source power|soil|smap|ndvi)  ·  gold_build
                                                  │
                         S3 lake silver/ y gold/  (Parquet, partición data_version)
                                                  │
                         Glue Data Catalog: fieldshift_silver, fieldshift_gold (sin crawlers)
                                                  │
                         Athena workgroup "fieldshift" + 6 vistas v_* (contrato con la API)
                                                  │
                         SSM /fieldshift/data_version  (versión vigente)
                                                  │
                  ─────────────── frontera DATA ↔ APP ───────────────
                                                  │
                         API (Lambda FastAPI, de BE/TL) consulta las vistas con WHERE cell_id = ?
```

### Componentes

| Pieza | Servicio | Configuración propuesta |
|---|---|---|
| Extracción | 4 Lambdas, **una imagen de contenedor** (un Dockerfile, un handler por fuente), arm64, Python 3.12 (requests, pandas, pyarrow, pyproj, rasterio, xarray/h5netcdf) | Timeout 15 min, 2-3 GB de memoria, **fuera de VPC** (sin NAT). Escriben solo en `raw/`. Credenciales de Earthdata desde Secrets Manager |
| Lake | S3 `fieldshift-lake-<cuenta>` | Block Public Access, cifrado SSE-S3, versionado con ciclo de vida (versiones no actuales a 7 días) |
| Transformación | Glue **Python shell** (no Spark), 0.0625 DPU | `library-set=analytics`; código compatible con Python 3.9 |
| Catálogo | Glue Data Catalog | Las tablas se registran al escribir con `awswrangler.s3.to_parquet(dataset=True, database=..., table=..., partition_cols=["data_version"], mode="overwrite_partitions")` |
| Consulta | Athena, workgroup `fieldshift` | Resultados en bucket propio `fieldshift-athena-results-<cuenta>` (ciclo de vida 7 días); límite de 1 GB escaneado por consulta; sin Lake Formation (rompe la reutilización de resultados) |
| Versión | SSM Parameter Store `/fieldshift/data_version` | Formato `YYYYMMDDHH`; lo escribe `gold_build` al final, solo si las pruebas de calidad pasan |
| Secretos | Secrets Manager `fieldshift/earthdata` | `{username, password}` de Earthdata Login |
| Imagen | ECR `fieldshift-ingest` | |
| Infraestructura como código | CloudFormation, **pila propia `fieldshift-data`** (`infra/data-stack.yaml`) | Separada de la pila de la app (de TL) para no chocar. Despliegue con `aws cloudformation deploy` |
| Costos | AWS Budgets 100 USD/mes | Alertas al 25/50/80 % (ya creado) |

### Por qué este reparto
- **Lambda para extraer:** cada fuente es una tarea corta e independiente (la más larga, SoilGrids, se reparte en 32 invocaciones de 1-3 min). Glue no trae GDAL ni NetCDF, así que los rasters y NetCDF se **aplanan a tabla en la Lambda** y Glue solo procesa tablas.
- **Glue Python shell para transformar:** los volúmenes son MB; Spark sería caro e innecesario.
- **Athena como frontera:** la API no lee archivos; consulta vistas estables. Si cambia el pipeline, el contrato no cambia.

---

## 4. Malla común de análisis

**EASE-Grid 2.0 global de 9 km** (la malla nativa de SMAP L4). Todas las fuentes se llevan a esta celda.

| Constante | Valor | Verificación |
|---|---|---|
| Proyección | EPSG:6933 | NSIDC |
| Dimensiones | 3856 columnas × 1624 filas | NSIDC |
| Lado de celda | 9008.055210146 m | NSIDC (9008.05) |
| Origen superior izquierdo | X0 = −17367530.44516138, Y0 = 7314540.830638 | NSIDC (2 decimales); prueba: N_COLS × lado = 2·\|X0\| |

- `cell_id = E9_r{fila:04d}_c{col:04d}`, fila = floor((Y0 − y)/lado), columna = floor((x − X0)/lado).
- Implementado y probado (`ingest/common/grid.py`, 7 pruebas): esquinas globales, cruce del ecuador, ida y vuelta del centroide, unicidad y conteo por zona.
- Toda tabla lleva `zone_id`, `cell_id`, `level` (`cell_9km`) y `resolution_m`, para admitir en el futuro un segundo nivel más fino (parcela).

### Cómo llega cada fuente a la celda

| Fuente | Resolución nativa | Regla |
|---|---|---|
| POWER | ~55 km (cuadro de 0.5°) | La serie del cuadro que contiene el centroide; varias celdas la comparten (`climate_shared_by_n_cells`) |
| SMAP L4 | 9 km | Valor directo (misma malla) |
| SRTM | 30 m | Valor en el centroide (MVP); media de la celda en V1 |
| MODIS NDVI | 250 m | Media, desviación y n válidos de los píxeles dentro de la celda |
| SoilGrids | 250 m | Media zonal + P05/P95 dentro de la celda |

---

## 5. Fuentes de datos del MVP

| # | Fuente | Organización | Variables | Resolución | Periodo usado | Acceso | Cuenta |
|---|---|---|---|---|---|---|---|
| 1 | **NASA POWER** (diario, comunidad AG) | NASA LaRC (meteorología MERRA-2) | Tmax, Tmin, Tmedia, lluvia, radiación, humedad relativa, viento a 2 m, viento máx. a 10 m, humedad de raíz de modelo | ~55 km, diaria | 1991-2025 a raw; análisis 2016-2025 | API REST por punto | No |
| 2 | **SMAP L4** `SPL4SMGP.008` | NASA JPL/GSFC, NSIDC | Humedad de raíz y de superficie | 9 km, cada 3 h | 2016-2025 | AppEEARS (puntos) | Earthdata |
| 3 | **SRTM** `SRTMGL1_NC.003` | NASA/NGA, LP DAAC | Elevación | 30 m | estático | AppEEARS (puntos) | Earthdata |
| 4 | **MODIS NDVI** `MOD13Q1.061` | NASA, LP DAAC | NDVI, confiabilidad del píxel | 250 m, 16 días | 2016-2025 | AppEEARS (área) | Earthdata |
| 5 | **SoilGrids 2.0** | ISRIC (no NASA), CC BY 4.0 | Arcilla, arena, limo, carbono orgánico, nitrógeno, CEC, pH, densidad aparente | 250 m, estático | — | WCS 2.0.1 | No |

**No satelitales (no son de DATA):** catálogo de cultivos (FAO EcoCrop + Kc FAO-56, lo cura SCI) y entradas del agricultor (rotación actual, riego, prioridades, exclusiones, calidad del agua de riego, historial de granizo).

**Sin fuente global útil (límites declarados):** fósforo, potasio y micronutrientes (se recomienda análisis de laboratorio), granizo y calidad del agua.

**Fuera del MVP (V1 o después):** GPM IMERG (lluvia de 10 km), GLDAS (humedad desde 2000), FAO GAEZ (aptitud por cultivo), CMS SOC Mexico (carbono a 90 m), ECOSTRESS, SIAP (precios y calendarios). Los recursos oficiales del reto que solo cubren EE. UU. (CDL, SSURGO, PRISM, NASS, OpenET, etc.) no aplican a México.

---

## 6. Detalle por fuente

### 6.1 NASA POWER — clima y viento
- **Endpoint:** `GET https://power.larc.nasa.gov/api/temporal/daily/point`
- **Parámetros:** `parameters=T2M_MAX,T2M_MIN,T2M,PRECTOTCORR,GWETROOT,ALLSKY_SFC_SW_DWN,RH2M,WS2M,WS10M_MAX`, `community=AG`, `latitude`, `longitude`, `start=19910101`, `end=20251231`, `format=JSON`, `time-standard=UTC`.
- **Verificado en la documentación oficial:**
  - máximo 20 parámetros por punto;
  - `WS10M_MAX` existe en DAILY/AG;
  - el día es LST (hora local) si no se pide UTC;
  - el valor de relleno es `-999`;
  - POWER advierte que puede bloquear a quien pide la misma ubicación repetidamente.
- **Llamadas:** una por **cuadro de 0.5°**, no por celda → ~10-15 llamadas en total. Caché en raw (si ya existe, no se vuelve a pedir) y pausa de 2 s.
- **Se guarda además:** las coordenadas y la elevación del cuadro que devuelve la respuesta (`power_cell_lat/lon`, `power_elev_m`).
- **Por comprobar en la primera respuesta:** las unidades de `WS10M_MAX` y de la radiación en el encabezado.
- **Plan B:** Zarr público `s3://nasa-power` (us-west-2, sin cuenta).

### 6.2 SMAP L4 — humedad del suelo
- **API AppEEARS:** `https://appeears.earthdatacloud.nasa.gov/api/`
  - `POST login` (basic auth de Earthdata) devuelve un token Bearer que dura ~48 h.
  - `POST task` envía la tarea; `GET task/{id}` da el estado.
  - `GET bundle/{id}` lista los archivos y `GET bundle/{id}/{file_id}` descarga cada uno.
- **Tarea:** tipo `point`, del `01-01-2016` al `12-31-2025` (formato `MM-DD-YYYY`), 136 coordenadas con `id = cell_id`.
- **Capas verificadas:**
  - `Geophysical_Data_sm_rootzone` (m³/m³, 0-100 cm);
  - `Geophysical_Data_sm_surface` (m³/m³, 0-5 cm);
  - `Geophysical_Data_sm_rootzone_pctl` (%; solo se usa para validar nuestro percentil);
  - todas float32, sin factor de escala, relleno `-9999`.
- **Límites:** AppEEARS **no documenta un máximo de puntos**. Al enviar se revisa `estimate.request_size`; si se rechaza o pasa más de 3 h en cola, se parte en 4 tareas (una por zona). Los enlaces de descarga duran 48 h y el bundle ~30 días.
- **Volumen esperado:** ~136 × 8 pasos/día × 3,650 días ≈ 4 M filas en CSV (cientos de MB en raw, unos MB en Parquet).
- **Plan B:** `GWETROOT` de POWER (fracción 0-1 a ~55 km), comparado **solo en percentiles**, nunca en valores absolutos. El gold V0 sale con este plan B y se reemplaza cuando llegue SMAP.

### 6.3 SRTM — elevación
- En la misma tarea de puntos que SMAP. **Pendiente:** verificar el nombre exacto de la capa con `GET /api/product/SRTMGL1_NC.003`.
- **Uso:** corrección de la temperatura de POWER por altura en cada celda:
  `t_adj = t_power − 6.5 °C/km × (cell_elev_m − power_elev_m) / 1000`
- **Por qué:** en el Sureste hay más de 1,500 m de desnivel dentro de un cuadro POWER. Sin corrección, las heladas de los valles altos se subestiman y las de la sierra se confunden con las del llano. Con la corrección, cada celda se comporta como su propia "subzona" sin dibujar subzonas a mano.
- El resultado se etiqueta como **estimación**; se guardan el valor crudo y el ajustado. La tasa de 6.5 °C/km es un parámetro (la aprueba SCI).

### 6.4 MODIS NDVI — cobertura vegetal (V1, pero se lanza ya)
- **Tarea:** tipo `area`, una por zona, con los polígonos de las celdas; salida NetCDF4 en proyección geográfica; 2016-2025.
- **Capas verificadas:**
  - `_250m_16_days_NDVI` (escala 0.0001, relleno −3000);
  - `_250m_16_days_pixel_reliability` (0-3, relleno −1);
  - `_250m_16_days_composite_day_of_the_year`.
- **Proceso:**
  - se conservan los píxeles con confiabilidad 0-1;
  - por celda y compuesto se calculan `ndvi_mean`, `ndvi_std` y `n_valid`;
  - el valor es nulo si quedan menos del 30 % de píxeles válidos;
  - se aplana en la Lambda.
- **Uso:** detectar suelo descubierto (NDVI < 0.25) en cada decena.
- **Plan B:** tarea por puntos en el centroide, o se omite la capa y se declara en la interfaz.

### 6.5 SoilGrids 2.0 — suelo
- **Endpoint:** WCS 2.0.1 `https://maps.isric.org/mapserv?map=/map/{var}.map`. La API REST de ISRIC está pausada sin fecha de regreso.
- **Cobertura:** `{var}_{profundidad}_{estadístico}` (por ejemplo `clay_0-5cm_mean`). Los subsets X/Y van en Homolosine (EPSG:152160), con el bbox de la zona + 0.1°, en GeoTIFF.
- **Volumen:** 288 recortes pequeños:
  - 8 variables;
  - 3 profundidades (0-5, 5-15 y 15-30 cm);
  - 3 estadísticos (`mean`, `Q0.05`, `Q0.95`);
  - 4 zonas.
- **En Lambda, en abanico:** una invocación por (zona, variable), 32 en total, de ~1-3 min cada una.
- **Factores de unidades verificados** (SoilGrids guarda enteros; se divide):

| Variable | Unidad guardada | ÷ | Unidad final |
|---|---|---|---|
| clay, sand, silt | g/kg | 10 | % |
| phh2o | pH×10 | 10 | pH |
| soc | dg/kg | 10 | g/kg |
| nitrogen | cg/kg | 100 | g/kg |
| cec | mmol(c)/kg | 10 | cmol(c)/kg |
| bdod | cg/cm³ | 100 | kg/dm³ |

- **Derivados:** materia orgánica estimada `om_pct_est = soc_g_kg × 1.724 ÷ 10` y clase textural USDA.
- **Plan B:** archivos COG/VRT de `files.isric.org/soilgrids/latest/data/` leídos por ventanas (sin verificar); último recurso, tabla regional fija curada por SCI.

---

## 7. Lake y capas

```
s3://fieldshift-lake-<cuenta>/
  raw/{source}/ingest_date=YYYY-MM-DD/...          respuesta tal cual + request.json (reprocesable sin volver a pedir)
  raw/appeears/tasks.json                          task_id y estado de las tareas de AppEEARS
  silver/{tabla}/data_version=YYYYMMDDHH/*.parquet
  gold/{tabla}/data_version=YYYYMMDDHH/*.parquet
```

- **raw (bronze):** inmutable, lo escribe solo Lambda.
- **silver:** una tabla por fuente, unidades limpias, rellenos → NULL, fechas en **UTC**, clave única.
- **gold:** indicadores agregados por celda × año × decena (36 decenas por año: días 1-10, 11-20, 21-fin de mes), climatología y suelo.
- **Versionado:** cada publicación es una partición `data_version` nueva. Las anteriores se conservan, así que se puede volver atrás cambiando el parámetro SSM y recreando las vistas.

---

## 8. Modelo de datos

### Silver

| Tabla | Clave | Columnas (unidad) |
|---|---|---|
| `zones` | `zone_id` | nombre, municipios, estado, bbox, n_cells |
| `cells` | `cell_id` | zone_id, row, col, lat, lon, geometry_wkt, cell_elev_m, power_cell_lat, power_cell_lon, power_elev_m, climate_shared_by_n_cells, level, resolution_m |
| `power_daily` | `cell_id, date` | tmax_c, tmin_c, tmean_c, tmax_adj_c, tmin_adj_c, precip_mm, rad_mj_m2, rh_pct, wind_ms, wind_max_ms, gwetroot_frac |
| `smap_daily` | `cell_id, date` | sm_root_m3m3, sm_surf_m3m3, sm_root_pctl_l4, n_obs, low_obs |
| `ndvi_16d` | `cell_id, date` | ndvi_mean, ndvi_std, n_valid |
| `soil` | `cell_id, depth_cm` | clay_pct, sand_pct, silt_pct, soc_g_kg, om_pct_est, nitrogen_g_kg, cec_cmol_kg, ph, bdod_kg_dm3 (+ `_p05`, `_p95`), texture_class |

Todas llevan `zone_id`.

### Gold

| Tabla | Clave | Contenido |
|---|---|---|
| `indicators_decade` | `cell_id, year, decade` | tmax_mean, tmin_mean, frost_days, frost_days_m2, hot_days_30/32/35/38, precip_mm, et0_mm, p_minus_et0_mm, heavy_rain_days, dry_spell_max_d, smp_mean, ws_days, ndvi_mean, bare_obs, precip_src, sm_src, complete |
| `climatology_decade` | `cell_id, decade` | frost_prob, frost_m2_prob, hot_prob_30/32/35/38, ws_prob, bare_prob, heavy_rain_prob, precip_p10/p50/p90, et0_p50, smp_p10/p50/p90, n_years, vulnerable, vulnerable_reasons |
| `indicators_year` | `cell_id, year` | totales y máximos anuales, wind_max_ms, windy_days, source_flags, complete_year |
| `soil_profile` | `cell_id, depth_cm` | copia de silver `soil` (la API solo lee gold) |
| `cells`, `zones` | — | copia de silver |
| `sources` | `source_id` | nombre, organización, producto y versión, URL, resolución, periodo, fecha de acceso, licencia, clase de dato |

`hot_days_*` se calcula con varios umbrales porque la API no lee series diarias: el motor elige el umbral más cercano a la temperatura crítica de cada cultivo.

### Indicadores (umbrales en `config/thresholds.yaml`; los aprueba SCI)

| Indicador | Definición por decena | Umbral inicial |
|---|---|---|
| `frost_days` / `frost_days_m2` | Días con Tmin ajustada < umbral | 0 °C / −2 °C |
| `hot_days_X` | Días con Tmax ajustada > X | 30, 32, 35, 38 °C |
| `heavy_rain_days` | Días con lluvia > umbral | 25 mm |
| `dry_spell_max_d` | Máxima racha de días con lluvia < umbral (cruza decenas) | 1 mm |
| `et0_mm` | ET de referencia Hargreaves-Samani (FAO-56): `0.0023 · 0.408·Ra · (Tmedia + 17.8) · √(Tmax − Tmin)`, con Ra por latitud y día del año (FAO-56 ec. 21) | — |
| `p_minus_et0_mm` | Lluvia − ET0 | — |
| `smp_mean` | Percentil de humedad dentro de la misma celda y decena (SMAP; si falta, GWETROOT) | — |
| `ws_days` | Días con percentil de humedad < umbral | 20 |
| `bare_obs` | NDVI < umbral | 0.25 |
| `windy_days` | Días con viento máximo > umbral | 10 m/s (por validar) |

- **Climatología:** probabilidad = fracción de años con al menos un evento en la decena, sobre la **ventana común 2016-2025** (10 años).
- **Decena vulnerable:** alguna probabilidad (o `bare_prob × heavy_rain_prob`) es mayor que el percentil 75 de la celda **y** ≥ 0.2. El piso evita marcar riesgos raros, porque el P75 solo siempre marca ~25 % de las decenas.
- **Precedencia de fuentes:** humedad SMAP > GWETROOT (en percentiles); lluvia POWER (IMERG en V1). La columna `*_src` registra cuál se usó.
- **Huecos:**
  - 1-2 días se interpolan, excepto la lluvia, que nunca se inventa;
  - una decena con más de 30 % de nulos queda con `complete = false`.

---

## 9. Contrato con la API (vistas de Athena)

La API consulta **solo estas vistas**, en la base `fieldshift_gold`, con `WHERE cell_id = ?` en una consulta parametrizada.

| Vista | Grano | Para qué endpoint |
|---|---|---|
| `v_cells` | 1 fila por celda | `POST /v1/fields`: polígono → celda dominante; `OUT_OF_REGION` si no existe |
| `v_cell_profile` | 36 filas por celda (decenas) | Perfil agroclimático y decenas vulnerables |
| `v_cell_indicators` | celda × año × decena | Puntaje por año histórico del motor |
| `v_cell_year` | celda × año | Series anuales |
| `v_cell_soil` | celda × profundidad | Reglas de pH y textura, salud del suelo |
| `v_sources` | 1 fila por fuente | `GET /v1/sources`, atribuciones |

- **Versión:** las vistas filtran la `data_version` vigente **por dentro** y no la exponen. `gold_build` las recrea (`CREATE OR REPLACE VIEW`) al publicar.
- **Reutilización de resultados de Athena:** máximo 60 min (no 7 días). Athena no detecta que cambió el dato debajo de una vista; por eso se usa una ventana corta y DATA avisa a BE en cada publicación (≤ 3 en el hackathon: V0, + SMAP, + NDVI).
- **Convenciones:**
  - la unidad va en el nombre de la columna (`_c`, `_mm`, `_pct`, `_m3m3`);
  - NULL = sin dato (nunca −999);
  - fechas en UTC;
  - agregar columnas no rompe el contrato; renombrar o quitar sí lo rompe.
- El documento completo del contrato (`docs/data_contract.md`) llevará un diccionario por columna (unidad, definición, umbral, fuente, clase, cuándo es NULL) y ejemplos marcados `_illustrative`.

---

## 10. Decisiones y su motivo

| # | Decisión | Motivo |
|---|---|---|
| 1 | Región us-west-2 | Ahí viven NASA Earthdata Cloud y `s3://nasa-power` |
| 2 | Malla EASE-Grid 2.0 de 9 km | Es la de SMAP; unidad común honesta |
| 3 | SMAP, SRTM y NDVI vía AppEEARS | Evita miles de HDF5 globales (SMAP L4 = 8 archivos/día) |
| 4 | SoilGrids vía WCS | La API REST de ISRIC está pausada |
| 5 | Una Lambda por fuente (contenedor arm64) | Tareas cortas e independientes; rasterio y NetCDF fuera de Glue |
| 6 | Glue Python shell 3.9, 2 jobs | Decisión del equipo; volumen en MB; sin Spark |
| 7 | Athena + vistas como frontera con la API | Contrato estable; SQL sobre el lake |
| 8 | Sin DynamoDB ni Lake Formation | Athena + caché en la API basta; Lake Formation rompe la reutilización de resultados |
| 9 | Ventana común 2016-2025 | Mismo periodo para todas las fuentes; evita mezclar 35 años de POWER con 10 de SMAP |
| 10 | Silver en UTC | Normalización única entre fuentes |
| 11 | Temperatura corregida por altura | La topografía de Coahuila hace poco representativo el cuadro de 55 km |
| 12 | Vistas sin `data_version` | Simplicidad para el MVP |
| 13 | Pila de datos separada de la pila de la app | Despliegues independientes entre DATA y TL |
| 14 | Envío inicial de AppEEARS desde la laptop | La cola tarda horas; se gana tiempo mientras se crea la infraestructura |

---

## 11. Costos, escala y riesgos

**Costo esperado de datos en el hackathon: < 5 USD.** Presupuesto: 100 USD/mes con alertas al 25/50/80 %.

- **Precios de referencia:**
  - S3: ~0.023 USD/GB-mes;
  - Athena: 5 USD/TB escaneado;
  - Glue: 0.44 USD/DPU-hora (Python shell usa 0.0625 DPU).
- **Datos en S3:** < 100 MB entre silver y gold, más los cientos de MB de raw de AppEEARS.

| Escala | Celdas | Cambio necesario |
|---|---|---|
| Piloto actual | 136 | Ninguno |
| Varios municipios | 250-500 | Ninguno (vigilar la cola de AppEEARS) |
| Un estado | ~1,900 | SMAP directo de S3 (Earthdata Cloud), POWER desde Zarr, SoilGrids por mosaicos |
| México | ~24,000 | Igual que un estado; < 10 USD/mes de almacenamiento y consulta |

El límite real no es el dinero sino el **tiempo de ingesta**.

| Riesgo | Señal | Mitigación |
|---|---|---|
| AppEEARS lento o rechaza la tarea | Más de 3 h en cola o error 4xx | 4 tareas por zona; gold V0 con GWETROOT |
| Servidor WCS de ISRIC caído | Errores 5xx en más de 3 coberturas | COG/VRT; tabla regional fija |
| POWER bloquea o limita | HTTP 429 | Caché y pausa; Zarr en S3 |
| Incompatibilidad Python 3.12 (Lambda) vs 3.9 (Glue) | SyntaxError o ImportError en Glue | Lint con objetivo py39 en `glue/`; prueba en contenedor 3.9 |
| La API ve datos viejos | Muestra la versión anterior tras publicar | Reutilización de 60 min + aviso |
| Costo inesperado | El presupuesto pasa del 25 % | Sin VPC/NAT; solo Python shell; límite de 1 GB por consulta; retención de logs de 7 días |
| Heladas mal representadas | La elevación de la celda difiere más de 300 m de la de POWER | Corrección por altura + bandera + texto de limitación |

---

## 12. Estado al cierre de este documento

| Elemento | Estado |
|---|---|
| Plan de datos | Aprobado por DATA |
| Configuración de zonas y umbrales | Hecha |
| Módulo de malla + pruebas | Hecho (7/7 pasan) |
| Lista de 136 celdas (CSV de puntos para AppEEARS, GeoJSON para revisar en el mapa) | Generada |
| Cuenta Earthdata + autorización de AppEEARS | Lista |
| Credenciales de Earthdata en archivo local `.env` (fuera de git) | Pendiente |
| Tareas de AppEEARS | No enviadas |
| Pila `fieldshift-data` en AWS | **No creada (decisión: validar antes de desplegar)** |
| Lambdas, jobs de Glue, vistas, contrato | No iniciados |
| Presupuesto AWS 100 USD | Creado |

**Orden de trabajo siguiente:**
1. Enviar las tareas de AppEEARS.
2. Desplegar la pila `fieldshift-data`.
3. Lambda POWER.
4. Lambda SoilGrids.
5. Funciones de indicadores con pruebas.
6. Job `silver_build`.
7. Job `gold_build` (incluye vistas y SSM).
8. Consultas de ejemplo, contrato y reporte de calidad.
9. Integrar SMAP, SRTM y NDVI cuando lleguen y publicar una nueva versión.

**Hitos (H0 = sáb 09:00):**

| Hora | Hito |
|---|---|
| H8 | Infraestructura + contrato v0 (sintético) para BE |
| H15 | Gold V0 de las 4 zonas en Athena |
| H18-H22 | SMAP integrado |
| H26-H30 | NDVI |
| H32 | Congelación de datos |

---

## 13. Qué pedimos validar al Solution Architect

1. **Cuenta AWS:** ¿lake y API viven en la misma cuenta? Si no, hay que agregar acceso entre cuentas (política del bucket, permisos de Glue y Athena) o compartir el catálogo.
2. **Frontera Lambda / Glue:** ¿de acuerdo con aplanar los rasters en Lambda y usar Glue solo para tablas?
3. **Glue Python shell 3.9:** AWS ya publica una guía para migrar fuera de Python shell. ¿Se acepta para el hackathon, o se prefiere hacer la transformación en la misma Lambda?
4. **Vistas sin `data_version` + reutilización de 60 min:** ¿suficiente para la API, o se prefiere exponer la versión y filtrar por ella (sin riesgo de datos viejos)?
5. **Orquestación:** invocación manual + `appeears_poll` cada 15 min, sin Step Functions. ¿Suficiente?
6. **Seguridad:** buckets privados con cifrado SSE-S3, Earthdata en Secrets Manager, roles de mínimo privilegio por Lambda y por job, Lambdas fuera de VPC. ¿Algún requisito adicional?
7. **IaC:** pila CloudFormation separada `fieldshift-data`. ¿Se integra al pipeline de CI/CD del equipo (GitHub Actions + OIDC) o se despliega a mano durante el hackathon?
8. **Ventana 2016-2025 (10 años):** las probabilidades van en pasos de 0.1. ¿Aceptable para el producto? (Decisión compartida con SCI.)
9. **Corrección por altura** con una tasa fija de 6.5 °C/km: ¿aceptable como estimación etiquetada? (Decisión compartida con SCI.)

---

## 14. Referencias oficiales (consultadas el 14-nov-2026)

- AppEEARS API: https://appeears.earthdatacloud.nasa.gov/api/ — productos `/api/product/SPL4SMGP.008`, `/api/product/MOD13Q1.061`
- NSIDC, guía de EASE-Grids: https://nsidc.org/data/user-resources/help-center/guide-ease-grids
- ISRIC SoilGrids, unidades y conversión: https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html
- ISRIC SoilGrids WCS: https://docs.isric.org/globaldata/soilgrids/wcs.html
- NASA POWER, API diaria: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
- NASA POWER en AWS: https://registry.opendata.aws/nasa-power/
- AWS Glue, jobs Python shell: https://docs.aws.amazon.com/glue/latest/dg/add-job-python.html
- Athena, reutilización de resultados: https://docs.aws.amazon.com/athena/latest/ug/reusing-query-results.html
- FAO-56 (ET de referencia): https://www.fao.org/4/x0490e/x0490e00.htm
