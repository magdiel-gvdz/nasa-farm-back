-- Validación de gold v1 (D-2026-11-15). Reemplazar :new y :old por las data_version a comparar
-- (old = 2026111500). Las tablas de gold son internas: estas consultas son solo para DATA.

-- 1) Regresión: los indicadores 2016-2025 no deben cambiar (n_diff = 0).
SELECT count(*) AS n_rows,
       sum(CASE WHEN abs(n.tmax_mean - o.tmax_mean) > 1e-9 OR abs(n.precip_mm - o.precip_mm) > 1e-9
                  OR abs(n.et0_mm - o.et0_mm) > 1e-9 OR n.frost_days <> o.frost_days
                  OR n.dry_spell_max_d <> o.dry_spell_max_d OR n.ws_days <> o.ws_days
                  OR n.hot_days_35 <> o.hot_days_35 OR n.complete <> o.complete THEN 1 ELSE 0 END) AS n_diff
FROM fieldshift_gold.indicators_decade n
JOIN fieldshift_gold.indicators_decade o
  ON o.cell_id = n.cell_id AND o.year = n.year AND o.decade = n.decade AND o.data_version = ':old'
WHERE n.data_version = ':new';

-- 2) Serie diaria: 1991-2025 completa y ET0 diaria = ET0 anual de v_cell_year (2016-2025).
SELECT min(date) AS first_day, max(date) AS last_day, count(*) AS n_rows,
       count(DISTINCT cell_id) AS n_cells, count_if(et0_mm IS NULL) AS et0_null
FROM fieldshift_gold.v_cell_daily;

SELECT max(abs(d.et0 - y.et0_mm)) AS max_abs_diff_mm
FROM (SELECT cell_id, year(date) AS year, sum(et0_mm) AS et0
      FROM fieldshift_gold.v_cell_daily WHERE year(date) >= 2016 GROUP BY 1, 2) d
JOIN fieldshift_gold.v_cell_year y ON y.cell_id = d.cell_id AND y.year = d.year;

-- 3) Terreno y suelo por zona: rangos con sentido físico.
SELECT t.zone_id, count(*) AS n_cells, round(approx_percentile(slope_mean_pct, 0.5), 2) AS slope_p50,
       round(max(slope_mean_pct), 1) AS slope_max, round(max(cold_air_pooling_share), 3) AS pool_max
FROM fieldshift_gold.v_cell_terrain t GROUP BY 1 ORDER BY 1;

SELECT zone_id, depth_cm, round(min(awc_mm_per_m), 1) AS awc_min, round(avg(awc_mm_per_m), 1) AS awc_avg,
       round(max(awc_mm_per_m), 1) AS awc_max, round(min(k_factor), 4) AS k_min, round(max(k_factor), 4) AS k_max
FROM fieldshift_gold.v_cell_soil GROUP BY 1, 2 ORDER BY 1, 2;
