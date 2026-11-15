-- API: serie diaria de una celda (escenarios y viento). ~3,650 filas, ~10 MB escaneados.
SELECT date, tmax_adj_c, tmin_adj_c, tmean_adj_c, precip_mm, wind_max_ms, rad_mj_m2, rh_pct, gwetroot_frac
FROM fieldshift_gold.v_cell_daily
WHERE cell_id = ?
ORDER BY date;
