-- 36 filas por celda (decenas): climatología 2016-2025 y decenas vulnerables.
-- Filtra la data_version vigente por dentro; gold_build la recrea al publicar ({data_version} se sustituye).
CREATE OR REPLACE VIEW fieldshift_gold.v_cell_profile AS
SELECT
  cell_id
, zone_id
, decade
, month
, frost_prob
, frost_m2_prob
, hot_prob_30
, hot_prob_32
, hot_prob_35
, hot_prob_38
, ws_prob
, bare_prob
, heavy_rain_prob
, windy_prob
, precip_p10
, precip_p50
, precip_p90
, et0_p50
, smp_p10
, smp_p50
, smp_p90
, n_years
, vulnerable
, vulnerable_reasons
, hot_prob_40
, frost_risk_prob
, data_version
FROM
  fieldshift_gold.climatology_decade
WHERE (data_version = '{data_version}')
