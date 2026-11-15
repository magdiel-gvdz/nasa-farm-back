-- Celda x día (2016-2025): serie meteorológica diaria para escenarios y viento (spec c4-daily-series).
-- Filtra la data_version vigente por dentro; gold_build la recrea al publicar ({data_version} se sustituye).
CREATE OR REPLACE VIEW fieldshift_gold.v_cell_daily AS
SELECT
  cell_id,
  zone_id,
  date,
  tmax_c,
  tmin_c,
  tmean_c,
  tmax_adj_c,
  tmin_adj_c,
  tmean_adj_c,
  temp_adj_applied,
  precip_mm,
  rad_mj_m2,
  rh_pct,
  wind_ms,
  wind_max_ms,
  gwetroot_frac
FROM fieldshift_gold.daily
WHERE data_version = '{data_version}'
