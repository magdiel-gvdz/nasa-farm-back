# Reporte de calidad de datos — Field Shift

> Versión publicada: `data_version = 2026111507` (Coahuila completo, 15-nov-2026). Cifras tomadas de Athena sobre
> las vistas `v_*`. Consultas reproducibles: `athena/queries/12_validation_quality.sql`,
> `14_validation_coahuila.sql`, `13_validation_gold_v1.sql`, `10_validation_dry_years.sql`,
> `11_validation_frost_by_elevation.sql`.
> **Cómo leer este reporte:** §1 y §8 describen la versión vigente (2,992 celdas, 5 regiones). Las §2-§7 son la
> validación histórica de las 136 celdas de las 4 zonas originales (`2026111500`/`2026111501`); siguen vigentes
> para esas celdas porque sus indicadores no cambiaron (§8.1).

## 1. Resumen

| Fuente | Estado | Cobertura | Observación principal |
|---|---|---|---|
| NASA POWER (clima diario) | En uso | 2,992 de 2,992 celdas, 1991-2025 en la serie diaria (indicadores 2016-2025), 0 días nulos | 84 cuadros de ~55 km; cada cuadro lo comparten de 8 a 49 celdas |
| SoilGrids 2.0 (suelo) | En uso | 2,992 de 2,992 celdas, 3 profundidades, 0 nulos | 28 celdas con menos del 80 % de píxeles válidos; 32 celdas con agua disponible < 30 mm/m (§8.3) |
| Copernicus DEM GLO-90 (elevación y terreno) | En uso | 2,992 de 2,992 celdas, 0 sin elevación | Fuente ESA, no NASA |
| SMAP L4 (humedad) | No se integra en el MVP | — | AppEEARS no entregó datos; se usa humedad de modelo de POWER |
| MODIS NDVI (vegetación) | No se integra en el MVP | — | AppEEARS no entregó datos; columnas de suelo descubierto vacías |

Todas las vistas tienen clave única (0 duplicados) y los conteos esperados (celdas × filas por celda):
`v_cells` 2,992, `v_cell_profile` 107,712, `v_cell_indicators` 1,077,120, `v_cell_year` 29,920,
`v_cell_soil` 8,976, `v_cell_daily` 38,249,728 (2,992 × 12,784 días), `v_cell_terrain` 2,992, `v_sources` 5.
Los jobs de Glue no escriben si falla alguna validación interna (unicidad, rangos, rellenos, cobertura).

**Alcance:** rectángulo que encierra a Coahuila, con partes de Nuevo León, Tamaulipas, Chihuahua, Durango,
Zacatecas y Texas (ver `data_contract.md` §3). Las regiones son rectángulos aproximados.

## 2. Clima (NASA POWER)

| Zona | Celdas | Cuadros POWER | Días-celda | Nulos | Tmin mín. | Tmax máx. | Lluvia máx. diaria | Viento máx. |
|---|---|---|---|---|---|---|---|---|
| Sureste | 45 | 2 | 164,385 | 0 | −5.8 °C | 39.5 °C | 106.0 mm | 17.2 m/s |
| La Laguna | 35 | 4 | 127,855 | 0 | −5.1 °C | 42.6 °C | 51.7 mm | 17.1 m/s |
| Norte | 20 | 4 | 73,060 | 0 | −8.3 °C | 45.6 °C | 88.6 mm | 16.0 m/s |
| Centro-Desierto | 36 | 2 | 131,508 | 0 | −8.1 °C | 45.1 °C | 88.2 mm | 15.2 m/s |

(Temperaturas crudas de POWER, antes de la corrección por altura.)

- Sin valores de relleno (`-999`), ningún día con Tmax < Tmin, todas las decenas completas (`complete = true`).
- Rangos dentro de lo esperado: Tmin −30 a 45 °C, lluvia 0 a 500 mm/día.
- **Limitación:** el Sureste (45 celdas) y el Centro (36 celdas) dependen de solo 2 cuadros POWER cada uno;
  lluvia, viento y humedad son iguales para todas las celdas de un mismo cuadro.
- La radiación de POWER viene de una malla más gruesa (1°); no se usa en los indicadores actuales.

## 3. Corrección de temperatura por altura

| Zona | Elevación de las celdas | Diferencia máx. con el cuadro POWER | Celdas con diferencia > 300 m | Heladas/año crudo → ajustado |
|---|---|---|---|---|
| Sureste | 1,193 - 2,500 m | 873 m | 19 | 5.2 → 11.1 |
| La Laguna | 1,095 - 1,279 m | 290 m | 0 | 2.9 → 1.8 |
| Norte | 305 - 528 m | 182 m | 0 | 4.6 → 4.8 |
| Centro-Desierto | 441 - 1,714 m | 752 m | 8 | 5.4 → 5.7 |

- La corrección usa una tasa fija de 6.5 °C/km: es una **estimación**. En 27 celdas la diferencia de altura
  supera 300 m; ahí el ajuste pasa de 2 °C y la incertidumbre es mayor.
- Comprobación de coherencia: las heladas aumentan con la altura (Sureste: 2.2 días/año bajo 1,500 m,
  8.5 entre 1,500 y 2,000 m, 24.9 sobre 2,000 m) y los días de calor > 35 °C disminuyen.
- Falta validar contra estaciones (SMN/CONAGUA) las heladas de la sierra de Arteaga.

## 4. Suelo (SoilGrids)

| Zona | Celdas | pH | Arcilla | Materia orgánica (est.) | Celdas con baja cobertura |
|---|---|---|---|---|---|
| Sureste | 45 | 7.11 - 8.40 | 22 - 37 % | 1.1 - 9.8 % | 2 |
| La Laguna | 35 | 8.09 - 8.56 | 23 - 36 % | 0.9 - 3.0 % | 3 |
| Norte | 20 | 7.83 - 8.04 | 27 - 40 % | 1.5 - 3.9 % | 0 |
| Centro-Desierto | 36 | 7.52 - 8.49 | 16 - 30 % | 0.9 - 7.0 % | 1 |

- Arena + limo + arcilla suma 100 % en todas las filas; media dentro de Q0.05-Q0.95 en todas.
- Cada celda promedia ~1,280 píxeles de 250 m.
- **Baja cobertura** (`low_coverage = true`, menos del 80 % de píxeles con dato; SoilGrids enmascara zonas
  urbanas y agua): `E9_r0463_c0846` (24 %, Saltillo), `E9_r0461_c0819` (27 %), `E9_r0461_c0820` (44 %) y
  `E9_r0462_c0820` (63 %) en La Laguna (zona urbana de Torreón), `E9_r0444_c0841` (34 %, Centro) y
  `E9_r0462_c0846` (67 %, Sureste). Tienen valor, calculado con menos píxeles.
- Valores altos de materia orgánica (hasta 9.8 %) corresponden a celdas de sierra con bosque; revisar con SCI
  si son creíbles para uso agrícola.

## 5. Indicadores

- Decenas vulnerables por celda (promedio): Sureste 16.8, Centro 13.9, La Laguna 12.8, Norte 12.2, de 36.
- Humedad: 100 % de las decenas con `smp_mean`, todas con `sm_src = power_gwetroot` (modelo, ~55 km).
- NDVI: 0 % de cobertura (`ndvi_mean`, `bare_obs`, `bare_prob` vacíos).
- Años más secos según POWER: La Laguna 2022 (113 mm), 2021 (135 mm), 2020 (152 mm); Centro 2025 (195 mm)
  y 2022 (198 mm). Pendiente contrastar con registros locales.

## 6. Validación de gold (15-nov-2026, `data_version = 2026111500`)

| # | Comprobación | Resultado |
|---|---|---|
| 1 | Conteos esperados y claves únicas en las 7 vistas; las vistas filtran la versión de SSM | Pasa (0 duplicados) |
| 2 | `v_cell_year` = suma de `v_cell_indicators` (lluvia, heladas, calor, ET0, lluvia intensa, racha seca) | Pasa (1,360 celda-años; diferencia máx. 1e-12 mm) |
| 3 | `v_cell_indicators` = recuento directo sobre `v_cell_daily` (días, heladas 0 y −2 °C, calor 30 y 35 °C, lluvia, Tmax media, viento) | Pasa (48,960 decenas; 0 diferencias) |
| 4 | Probabilidades de `v_cell_profile` = fracción de años con evento (helada, calor, lluvia intensa, estrés hídrico) | Pasa (4,896 filas; 0 diferencias) |
| 5 | Invariantes: probabilidades en [0, 1], 10 años y 36 decenas por celda, calor 30 ≥ 32 ≥ 35 ≥ 38, helada −2 ≤ helada 0, P10 ≤ P50 ≤ P90, `vulnerable` coherente con sus motivos | Pasa (0 violaciones) |
| 6 | Estacionalidad: heladas de noviembre a marzo, calor > 35 °C de abril a septiembre, lluvia máxima de junio a septiembre | Pasa en las 4 zonas |
| 7 | ET0 anual Hargreaves-Samani | 1,269-1,887 mm; plausible para clima semiárido. Por revisar con SCI |
| 8 | Humedad (percentil de GWETROOT) frente a lluvia anual | Correlación 0.70-0.87 por zona: coherente |
| 9 | Heladas crecen con la altura y calor decrece (corrección por altura) | Pasa (Sureste: 2.2 → 8.5 → 24.9 heladas/año por banda) |
| 10 | Contraste con normales 1991-2020 del SMN (fuente secundaria, ver abajo) | Pasa en lluvia y temperatura media; ver diferencias |

**Contraste externo.** Normales 1991-2020 de CONAGUA/SMN tomadas de Climate-Zone (las tablas oficiales del
SMN no respondieron el 15-nov). Periodos distintos: normales 1991-2020 frente a gold 2016-2025.

| Estación SMN | Celda gold | Lluvia anual SMN / gold | Sesgo medio Tmax | Sesgo medio Tmin |
|---|---|---|---|---|
| Saltillo (DGE) | `E9_r0463_c0846` (1,651 m) | 330 / 333 mm (+1 %) | +2.0 °C | +0.6 °C |
| Torreón (Presa Coyote) | `E9_r0461_c0820` (1,123 m) | 211 / 217 mm (+3 %) | −0.7 °C | +0.2 °C |

- La lluvia anual y su reparto mensual coinciden bien; la mayor diferencia mensual es noviembre en Saltillo
  (9 frente a 17 mm).
- Saltillo sale ~2 °C más cálido en máximas en todos los meses: parte puede ser el periodo más reciente y
  parte el sesgo del cuadro de ~55 km. Afecta a `hot_days_*` (posible sobreestimación de calor en el Sureste).
- Las mínimas medias coinciden, pero eso **no** valida el número de heladas: el reanálisis tiende a
  suavizar los extremos fríos de los valles. Validar los días con helada requiere datos diarios de estación.
- Nota: la primera helada de otoño cae el mismo día en las 4 zonas (mediana día 342) porque las heladas
  llegan con frentes fríos que cubren toda la región (24-dic-2022 heló en las 136 celdas). No es un error.

## 7. Validación de gold v1 (15-nov-2026, `data_version = 2026111501`)

Cambios: `v_cell_daily` 1991-2025 + `et0_mm` diaria; vista nueva `v_cell_terrain`; `v_cell_soil` suma
`wv0033_m3m3`, `wv1500_m3m3`, `awc_mm_per_m` y `k_factor`. Consultas: `athena/queries/13_validation_gold_v1.sql`.

| Prueba | Resultado |
|---|---|
| Regresión: `indicators_decade` nueva vs `2026111500` (48,960 filas; Tmax, lluvia, ET0, heladas, racha seca, estrés hídrico, calor 35, completitud) | **0 diferencias** |
| `v_cell_daily`: fechas, filas, celdas, `et0_mm` nula | 1991-01-01 a 2025-12-31, 1,738,624 filas, 136 celdas, 0 nulos |
| Σ `et0_mm` diaria por año vs `v_cell_year.et0_mm` (2016-2025) | diferencia máxima 3 × 10⁻¹² mm |
| Claves únicas de las 8 vistas | 0 duplicados |
| Elevación media del terreno vs `cell_elev_m` publicada | idéntica (mismos píxeles, 0.0 m) |
| Una celda de `v_cell_daily` | ~17 MB escaneados (límite 1 GB) |

**Terreno (sentido físico).** Pendiente media por zona (mediana): Laguna 0.5 %, Norte 1.1 %, Centro 8.6 %,
Sureste 14.7 %; máximo 40 % (sierras de Centro). Derramadero (`E9_r0465_c0843`) 2.8 % y Arteaga
(`E9_r0463_c0847`) 20.6 % (P90 54 %), como se espera de valle contra sierra. Bajío frío: la fracción por celda es
pequeña (máximo 6.8 % en La Laguna, 0.3 % en el Norte); es un indicador relativo, no una medición.

**Agua disponible y factor K.** `awc_mm_per_m` entre 46 y 173 mm/m (media por zona 98-134), dentro del rango
típico de suelos minerales. El punto de marchitez sigue a la arcilla (correlación 0.9 en Sureste y Centro), pero
la capacidad de campo de SoilGrids casi no lo hace (correlación −0.24 a 0.28), así que el AWC **no** ordena las
texturas como el libro (franco-arenoso 139 mm/m > franco 110). La incertidumbre del modelo es grande (capacidad
de campo P05-P95 ≈ 0.09-0.43 m³/m³): usar el AWC como orden de magnitud zonal, no para ordenar celdas vecinas.
`k_factor` entre 0.016 y 0.023 t·ha·h/(ha·MJ·mm) (erosionabilidad baja a moderada); la fórmula EPIC de Williams
da un rango estrecho y no incluye estructura ni permeabilidad.

**Unidades verificadas:** `wv0033`/`wv1500` de SoilGrids vienen en 10⁻³ cm³/cm³ (FAQ de ISRIC) → ÷1000. El
factor de K se tomó de SWAT+ (ec. 4:1.1.5-9) y el paso a unidades SI con 0.1317 (Foster et al., 1981; **verificar**
contra la fuente original).

## 8. Validación de Coahuila completo (15-nov-2026, `data_version = 2026111507`)

Cambio: de 136 a 2,992 celdas, POWER guardado por cuadro (84) con ajuste por altura y ET0 en la vista
`v_cell_daily`, suelo y terreno procesados en 30 bloques de 1°. Consultas: `athena/queries/14_validation_coahuila.sql`.

### 8.1 Regresión y estructura

| Prueba | Resultado |
|---|---|
| Indicadores de las 136 celdas antiguas vs `2026111501`, **todas** las columnas: `indicators_decade` (48,960 filas, 27 columnas), `climatology_decade` (4,896), `indicators_year` (1,360) | **0 diferencias** |
| Terreno de las 136 celdas antiguas (136 filas, 14 columnas) | 0 diferencias |
| Conteos = celdas × esperado y claves únicas en las 8 vistas | Pasa (0 duplicados) |
| `v_cell_daily` de Derramadero (`E9_r0465_c0843`) y Arteaga (`E9_r0463_c0847`) vs versión anterior | Mismas 17 columnas en el mismo orden, 12,784 filas, valores idénticos (máx. diferencia `et0_mm` 4 × 10⁻¹⁵ mm) |
| Σ `et0_mm` diaria por año vs `v_cell_year.et0_mm` (2016-2025, 2,992 celdas) | diferencia máx. 4 × 10⁻¹² mm |
| Serie diaria | 1991-01-01 a 2025-12-31, 2,992 celdas, 0 nulos en temperatura, lluvia y `et0_mm`; 0 días con Tmax < Tmin |
| Decenas incompletas / humedad nula en `v_cell_indicators` | 0 / 0 |
| Bytes escaneados por consulta de una celda | máx. 37.5 MB (`v_cell_indicators`); `v_cell_daily` 15 MB (antes 57 MB); resto < 3 MB |

### 8.2 Sentido físico por región

| Región | Celdas | Cuadros POWER | Elevación mediana (rango) | Pendiente mediana | Heladas/año | Días > 35 °C/año | Lluvia anual | Decenas vulnerables (prom.) |
|---|---|---|---|---|---|---|---|---|
| Sureste | 621 | 25 | 1,582 m (296-2,740) | 11.6 % | 9.1 | 39.3 | 394 mm | 16.2 |
| La Laguna | 391 | 15 | 1,353 m (852-2,121) | 7.1 % | 3.9 | 61.2 | 256 mm | 16.9 |
| Centro-Desierto | 1,260 | 40 | 1,136 m (416-2,151) | 9.9 % | 12.4 | 72.8 | 309 mm | 19.3 |
| Carbonífera | 336 | 12 | 369 m (154-1,508) | 2.0 % | 3.6 | 123.2 | 428 mm | 13.4 |
| Norte | 384 | 15 | 357 m (179-697) | 2.3 % | 6.6 | 118.5 | 445 mm | 17.5 |

(Heladas, calor y lluvia: promedios 2016-2025 con temperatura ajustada por altura. Un cuadro POWER puede tocar
dos regiones, por eso la suma de cuadros es mayor que 84.)

- El Sureste es el más alto, con más pendiente y menos calor; Carbonífera y Norte son bajos, calientes y los más
  lluviosos; La Laguna es la más seca. Coincide con la geografía conocida del estado.
- Las heladas crecen con la altura (correlación 0.52 entre elevación y heladas/año en las 2,992 celdas). El Centro
  tiene más heladas que el Sureste pese a ser más bajo: desierto con mucha oscilación diaria; revisar con SCI.
- ET0 anual media por celda: 1,232-1,864 mm.

| Región | Tmin mín. | Tmax máx. | Lluvia máx. diaria | Viento máx. | pH | Arcilla | MO (est.) | Celdas con baja cobertura de suelo |
|---|---|---|---|---|---|---|---|---|
| Sureste | −10.5 °C | 46.2 °C | 217.8 mm | 18.6 m/s | 6.8-8.7 | 15-45 % | 0.8-12.8 % | 13 |
| La Laguna | −10.4 °C | 42.6 °C | 92.4 mm | 19.5 m/s | 7.3-8.8 | 18-41 % | 0.8-6.3 % | 3 |
| Centro-Desierto | −12.6 °C | 46.2 °C | 122.3 mm | 19.5 m/s | 7.0-8.7 | 13-47 % | 0.9-10.5 % | 1 |
| Carbonífera | −9.9 °C | 47.4 °C | 136.2 mm | 17.2 m/s | 7.3-8.4 | 18-41 % | 1.1-7.8 % | 3 |
| Norte | −12.7 °C | 47.3 °C | 106.0 mm | 18.5 m/s | 6.5-8.1 | 22-43 % | 1.3-12.6 % | 8 |

(Temperaturas crudas de POWER, 1991-2025.) `awc_mm_per_m` 5.5-176.7 mm/m; `k_factor` 0.015-0.024.
La lluvia diaria de 217.8 mm en el Sureste es el máximo de 35 años en la región; está dentro del rango de prueba
(0-500 mm) y es plausible para un evento tropical, pero conviene confirmar la fecha con SCI.

### 8.3 Hallazgos (para SCI)

1. **El suelo de las 136 celdas antiguas cambió poco** respecto a `2026111501`, porque SoilGrids ahora se procesa
   en bloques de 1° en lugar de recortes por zona: −0.26 % de píxeles; arcilla ±0.05 puntos y AWC ±0.5 mm/m en
   promedio (máx. 0.5 puntos y 2.3 mm/m); pH máx. 0.04. Dos celdas cambian de clase textural por estar en el
   límite entre clases: `E9_r0425_c0849` 15-30 cm (*clay loam* → *sandy clay loam*) y `E9_r0461_c0819` 15-30 cm
   (*loam* → *clay loam*). Los indicadores climáticos no cambiaron.
2. **32 celdas con `awc_mm_per_m` < 30 mm/m**, sobre todo en `coah-carbonifera` a 15-30 cm (mínimo 5.5 mm/m en
   `E9_r0433_c0848`). SoilGrids da `wv0033` ≈ `wv1500` (por ejemplo 0.188 y 0.182 m³/m³) en suelos
   franco-arcillosos, donde la tabla de textura esperaría ~150 mm/m. Es un artefacto de la fuente, no del pipeline.
   SCI decide si el motor lo trata como dato poco confiable (por ejemplo, usar la profundidad 0-5 cm o un valor
   por textura cuando AWC < 30).
3. **En el historial de Glue, la corrida de `fieldshift-gold-build` del 15-nov aparece en `FAILED` a propósito**:
   se corrió con un parámetro SSM de prueba para escribir tablas y vistas sin publicar hasta validar. El único error
   fue `AccessDenied` al escribir ese parámetro; `/fieldshift/data_version` se publicó a mano tras la validación.

## 9. Pendientes de calidad

1. SMAP y NDVI no se integran en el MVP (decisión C1); retomarlos solo si se reabre AppEEARS.
2. Decidir con SCI el tratamiento de las 32 celdas con AWC < 30 mm/m (§8.3) y revisar las heladas del Centro (§8.2).
3. Validar días con helada contra datos diarios de estación (CLICOM/SMN); confirmar el sesgo cálido de Tmax en Saltillo.
4. Confirmar con SCI los umbrales (viento 10 m/s, calor 35 °C para vulnerabilidad, piso de 0.2) y los de terreno
   (bajío: 15 m bajo la media de 1 km y pendiente < 3 %).
5. Confirmar el factor 0.1317 de K con la fuente original y, si hay tiempo, contrastar el AWC con una tabla de
   retención por textura (por ejemplo Saxton y Rawls, 2006).
