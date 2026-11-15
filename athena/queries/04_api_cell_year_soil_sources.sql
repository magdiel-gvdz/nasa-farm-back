-- API: series anuales de una celda.
SELECT year, tmax_mean, tmin_mean, frost_days, hot_days_35, precip_mm, et0_mm, p_minus_et0_mm,
       dry_spell_max_d, ws_days, wind_max_ms, windy_days, complete_year, source_flags
FROM fieldshift_gold.v_cell_year
WHERE cell_id = ?
ORDER BY year;

-- API: suelo de una celda (3 profundidades).
SELECT depth_cm, clay_pct, sand_pct, silt_pct, texture_class, ph, ph_p05, ph_p95, om_pct_est,
       nitrogen_g_kg, cec_cmol_kg, bdod_kg_dm3, valid_pixel_pct, low_coverage
FROM fieldshift_gold.v_cell_soil
WHERE cell_id = ?
ORDER BY depth_top_cm;

-- API: fuentes y atribuciones.
SELECT source_id, name, organization, product_version, url, resolution, period, access_date, license,
       data_class, status, used_for
FROM fieldshift_gold.v_sources
ORDER BY status, source_id;
