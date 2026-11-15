-- API: indicadores por año y decena de una celda (360 filas) para el puntaje por año histórico.
SELECT year, decade, n_days, tmax_mean, tmin_mean, frost_days, frost_days_m2, hot_days_30, hot_days_32,
       hot_days_35, hot_days_38, precip_mm, et0_mm, p_minus_et0_mm, heavy_rain_days, dry_spell_max_d,
       smp_mean, ws_days, wind_max_ms, windy_days, sm_src, temp_adj_applied, complete
FROM fieldshift_gold.v_cell_indicators
WHERE cell_id = ?
ORDER BY year, decade;
