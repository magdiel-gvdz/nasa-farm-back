-- Celda x año: totales y máximos anuales.
-- Filtra la data_version vigente por dentro; gold_build la recrea al publicar ({data_version} se sustituye).
CREATE OR REPLACE VIEW fieldshift_gold.v_cell_year AS
SELECT
  cell_id,
  zone_id,
  year,
  tmax_mean,
  tmin_mean,
  frost_days,
  frost_days_m2,
  hot_days_30,
  hot_days_32,
  hot_days_35,
  hot_days_38,
  precip_mm,
  et0_mm,
  p_minus_et0_mm,
  heavy_rain_days,
  dry_spell_max_d,
  ws_days,
  wind_max_ms,
  windy_days,
  n_decades_complete,
  complete_year,
  source_flags
FROM fieldshift_gold.indicators_year
WHERE data_version = '{data_version}'
