-- API: terreno de una celda (Copernicus DEM GLO-90). Una fila.
-- aspect_dominant NULL = celda plana (ningún píxel con pendiente > 2 %). cold_air_pooling_share = estimación.
SELECT elev_mean_m, elev_min_m, elev_max_m, elev_std_m, slope_mean_pct, slope_p90_pct,
       aspect_dominant, aspect_dominant_share, cold_air_pooling_share
FROM fieldshift_gold.v_cell_terrain
WHERE cell_id = ?;

-- Agua disponible en los primeros 30 cm (mm), ponderando cada capa por su espesor.
SELECT sum(awc_mm_per_m * (depth_bottom_cm - depth_top_cm) / 100.0) AS awc_0_30cm_mm
FROM fieldshift_gold.v_cell_soil
WHERE cell_id = ?;
