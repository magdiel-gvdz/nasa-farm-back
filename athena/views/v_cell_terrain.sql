-- Celda: terreno desde Copernicus DEM GLO-90 (~90 m). Pendiente, orientación y bajío frío son estimaciones.
-- Filtra la data_version vigente por dentro; gold_build la recrea al publicar ({data_version} se sustituye).
CREATE OR REPLACE VIEW fieldshift_gold.v_cell_terrain AS
SELECT
  cell_id,
  zone_id,
  elev_mean_m,
  elev_min_m,
  elev_max_m,
  elev_std_m,
  slope_mean_pct,
  slope_p90_pct,
  aspect_dominant,
  aspect_dominant_share,
  cold_air_pooling_share,
  n_pixels
FROM fieldshift_gold.terrain
WHERE data_version = '{data_version}'
