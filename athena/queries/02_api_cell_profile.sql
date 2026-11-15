-- API: perfil agroclimático de una celda (36 decenas). Parámetro: cell_id.
SELECT decade, month, frost_prob, frost_m2_prob, hot_prob_30, hot_prob_35, heavy_rain_prob, ws_prob,
       windy_prob, precip_p10, precip_p50, precip_p90, et0_p50, n_years, vulnerable, vulnerable_reasons
FROM fieldshift_gold.v_cell_profile
WHERE cell_id = ?
ORDER BY decade;
