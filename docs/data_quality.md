# Reporte de calidad de datos — Field Shift

> Versión publicada: `data_version = 2026111500` (14-nov-2026). Cifras tomadas de Athena sobre las vistas `v_*`.
> Consultas reproducibles: `athena/queries/12_validation_quality.sql`, `10_validation_dry_years.sql`,
> `11_validation_frost_by_elevation.sql`.

## 1. Resumen

| Fuente | Estado | Cobertura | Observación principal |
|---|---|---|---|
| NASA POWER (clima diario) | En uso | 136 de 136 celdas, 2016-2025, 0 días nulos | 12 cuadros de ~55 km para 136 celdas |
| SoilGrids 2.0 (suelo) | En uso | 136 de 136 celdas, 3 profundidades, 0 nulos | 6 celdas con menos del 80 % de píxeles válidos |
| Copernicus DEM GLO-90 (elevación) | En uso | 136 de 136 celdas | Fuente ESA, no NASA |
| SMAP L4 (humedad) | Pendiente (AppEEARS en proceso) | — | Se usa humedad de modelo de POWER |
| MODIS NDVI (vegetación) | Pendiente (AppEEARS en cola) | — | Columnas de suelo descubierto vacías |

Todas las vistas tienen clave única (0 duplicados) y los conteos esperados: `v_cells` 136, `v_cell_profile`
4,896, `v_cell_indicators` 48,960, `v_cell_year` 1,360, `v_cell_soil` 408, `v_cell_daily` 496,808, `v_sources` 5.
Los jobs de Glue no publican si falla alguna validación (unicidad, rangos, rellenos, cobertura).

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

## 7. Pendientes de calidad

1. Integrar SMAP y comparar el percentil propio con `sm_rootzone_pctl` (alerta si la correlación es < 0.8).
2. Integrar NDVI y revisar cobertura de píxeles válidos por celda.
3. Validar días con helada contra datos diarios de estación (CLICOM/SMN); confirmar el sesgo cálido de Tmax en Saltillo.
4. Confirmar con SCI los umbrales (viento 10 m/s, calor 35 °C para vulnerabilidad, piso de 0.2).
