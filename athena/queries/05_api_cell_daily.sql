-- API: serie diaria de una celda, 1991-2025 (escenarios, heladas P10/P90, viento extremo, demanda de agua).
-- ~12,784 filas por celda. et0_mm = ET de referencia diaria (Hargreaves-Samani); demanda de un cultivo = Σ et0_mm × Kc.
SELECT date, tmax_adj_c, tmin_adj_c, tmean_adj_c, precip_mm, et0_mm, wind_max_ms, rad_mj_m2, rh_pct, gwetroot_frac
FROM fieldshift_gold.v_cell_daily
WHERE cell_id = ?
ORDER BY date;
