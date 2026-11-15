-- Celda x año x decena: indicadores para el puntaje por año histórico.
-- Filtra la data_version vigente por dentro; gold_build la recrea al publicar ({data_version} se sustituye).
CREATE OR REPLACE VIEW fieldshift_gold.v_cell_indicators AS
SELECT
  cell_id
, zone_id
, year
, decade
, month
, n_days
, tmax_mean
, tmin_mean
, frost_days
, frost_days_m2
, hot_days_30
, hot_days_32
, hot_days_35
, hot_days_38
, precip_mm
, et0_mm
, p_minus_et0_mm
, heavy_rain_days
, dry_spell_max_d
, smp_mean
, ws_days
, wind_max_ms
, windy_days
, ndvi_mean
, bare_obs
, precip_src
, sm_src
, temp_adj_applied
, complete
, hot_days_40
, frost_risk_days
, data_version
FROM
  fieldshift_gold.indicators_decade
WHERE (data_version = '{data_version}')
