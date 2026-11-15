-- Validación de Coahuila completo (etapa 5, 15-nov-2026). Solo para DATA: usa tablas internas de gold.
-- Reemplazar :new y :old por las data_version a comparar (new = 2026111507, old = 2026111501).
-- La regresión de TODAS las columnas se generó con un script que arma un CASE por columna desde el Glue Catalog;
-- aquí quedan las columnas principales (resultado esperado: n_diff = 0 en las tres tablas).

-- 1) Regresión de indicadores en las celdas comunes (n_rows = 136 × 360 = 48,960).
SELECT count(*) AS n_rows,
       sum(CASE WHEN abs(n.tmax_mean - o.tmax_mean) > 1e-9 OR abs(n.tmin_mean - o.tmin_mean) > 1e-9
                  OR abs(n.precip_mm - o.precip_mm) > 1e-9 OR abs(n.et0_mm - o.et0_mm) > 1e-9
                  OR abs(n.smp_mean - o.smp_mean) > 1e-9 OR n.frost_days <> o.frost_days
                  OR n.frost_days_m2 <> o.frost_days_m2 OR n.hot_days_35 <> o.hot_days_35
                  OR n.dry_spell_max_d <> o.dry_spell_max_d OR n.ws_days <> o.ws_days
                  OR n.windy_days <> o.windy_days OR n.complete <> o.complete THEN 1 ELSE 0 END) AS n_diff
FROM fieldshift_gold.indicators_decade n
JOIN fieldshift_gold.indicators_decade o
  ON o.cell_id = n.cell_id AND o.year = n.year AND o.decade = n.decade AND o.data_version = ':old'
WHERE n.data_version = ':new';

-- 2) Regresión de climatología (n_rows = 136 × 36 = 4,896) y años (136 × 10 = 1,360).
SELECT count(*) AS n_rows,
       sum(CASE WHEN abs(n.frost_prob - o.frost_prob) > 1e-9 OR abs(n.hot_prob_35 - o.hot_prob_35) > 1e-9
                  OR abs(n.precip_p50 - o.precip_p50) > 1e-9 OR abs(n.smp_p50 - o.smp_p50) > 1e-9
                  OR n.vulnerable <> o.vulnerable THEN 1 ELSE 0 END) AS n_diff
FROM fieldshift_gold.climatology_decade n
JOIN fieldshift_gold.climatology_decade o
  ON o.cell_id = n.cell_id AND o.decade = n.decade AND o.data_version = ':old'
WHERE n.data_version = ':new';

SELECT count(*) AS n_rows,
       sum(CASE WHEN abs(n.precip_mm - o.precip_mm) > 1e-9 OR abs(n.et0_mm - o.et0_mm) > 1e-9
                  OR n.frost_days <> o.frost_days OR n.hot_days_35 <> o.hot_days_35 THEN 1 ELSE 0 END) AS n_diff
FROM fieldshift_gold.indicators_year n
JOIN fieldshift_gold.indicators_year o
  ON o.cell_id = n.cell_id AND o.year = n.year AND o.data_version = ':old'
WHERE n.data_version = ':new';

-- 3) Suelo de las celdas comunes: magnitud del cambio por procesar en bloques de 1° (esperado: pequeño, no 0).
SELECT n.depth_cm, count(*) AS n,
       round(avg(abs(n.clay_pct - o.clay_pct)), 3) AS clay_avg_abs, round(max(abs(n.clay_pct - o.clay_pct)), 2) AS clay_max_abs,
       round(max(abs(n.ph - o.ph)), 2) AS ph_max_abs,
       round(avg(abs(n.awc_mm_per_m - o.awc_mm_per_m)), 2) AS awc_avg_abs, round(max(abs(n.awc_mm_per_m - o.awc_mm_per_m)), 2) AS awc_max_abs,
       count_if(n.texture_class <> o.texture_class) AS texture_changes
FROM fieldshift_gold.soil_profile n
JOIN fieldshift_gold.soil_profile o
  ON o.cell_id = n.cell_id AND o.depth_cm = n.depth_cm AND o.data_version = ':old'
WHERE n.data_version = ':new'
GROUP BY 1 ORDER BY 1;

-- 4) Sentido físico por región (sobre las vistas vigentes).
WITH y AS (SELECT cell_id, avg(frost_days) AS frost, avg(hot_days_35) AS hot35, avg(precip_mm) AS p
           FROM fieldshift_gold.v_cell_year GROUP BY 1)
SELECT c.zone_id, count(*) AS n_cells,
       round(approx_percentile(c.cell_elev_m, 0.5)) AS elev_p50, round(min(c.cell_elev_m)) AS elev_min, round(max(c.cell_elev_m)) AS elev_max,
       round(approx_percentile(t.slope_mean_pct, 0.5), 2) AS slope_p50,
       round(avg(y.frost), 1) AS frost_d_yr, round(avg(y.hot35), 1) AS hot35_d_yr, round(avg(y.p)) AS precip_mm_yr
FROM fieldshift_gold.v_cells c
JOIN fieldshift_gold.v_cell_terrain t ON t.cell_id = c.cell_id
JOIN y ON y.cell_id = c.cell_id
GROUP BY 1 ORDER BY 1;

WITH y AS (SELECT cell_id, avg(frost_days) AS frost FROM fieldshift_gold.v_cell_year GROUP BY 1)
SELECT round(corr(c.cell_elev_m, y.frost), 3) AS r_elev_frost
FROM fieldshift_gold.v_cells c JOIN y ON y.cell_id = c.cell_id;

-- 5) Agua disponible muy baja (hallazgo de la fuente: wv0033 ≈ wv1500). Filas por región y profundidad;
--    en 2026111507 son 32 celdas distintas (count(DISTINCT cell_id)).
SELECT s.zone_id, s.depth_cm, count(*) AS n, round(min(s.awc_mm_per_m), 1) AS awc_min
FROM fieldshift_gold.v_cell_soil s
WHERE s.awc_mm_per_m < 30
GROUP BY 1, 2 ORDER BY 1, 2;

-- 6) Bytes escaneados: correr cada vista con WHERE cell_id = '<celda>' y revisar DataScannedInBytes
--    (2026111507: v_cell_indicators 37.5 MB, v_cell_daily 15 MB, resto < 3 MB; límite del criterio 100 MB).
