-- Celda x día (1991-2025): serie meteorológica diaria para escenarios y viento (spec c4-daily-series).
-- Filtra la data_version vigente por dentro; gold_build la recrea al publicar ({data_version} se sustituye).
--
-- Desde la etapa 2 (decisión C4) gold guarda UNA serie por cuadro POWER (power_square_daily, ~55 km) y esta
-- vista la reparte a las celdas de 9 km. Mismas columnas y valores que la tabla daily por celda de 2026111501:
--   *_adj_c = valor POWER - cells.temp_delta_c   (corrección por altura, estimación; 0 si la celda no tiene DEM)
--   et0_mm  = Hargreaves-Samani FAO-56 ec. 52 con Ra de FAO-56 ec. 21 (latitud de la celda, día del año).
-- Las operaciones siguen el mismo orden que glue/lib/indicators.py (et0_hargreaves, extraterrestrial_radiation)
-- para dar el mismo double; tests/athena/test_v_cell_daily.py lo compara contra Python con DuckDB.
-- Literales con E0 = DOUBLE (sin E serían DECIMAL y cambiarían el redondeo). CASE en lugar de greatest/least
-- para que un NULL siga siendo NULL en cualquier motor.
CREATE OR REPLACE VIEW fieldshift_gold.v_cell_daily AS
WITH adj AS (
  SELECT
    c.cell_id,
    c.zone_id,
    d.date,
    d.tmax_c,
    d.tmin_c,
    d.tmean_c,
    d.tmax_c - c.temp_delta_c AS tmax_adj_c,
    d.tmin_c - c.temp_delta_c AS tmin_adj_c,
    d.tmean_c - c.temp_delta_c AS tmean_adj_c,
    c.temp_adj_applied,
    d.precip_mm,
    d.rad_mj_m2,
    d.rh_pct,
    d.wind_ms,
    d.wind_max_ms,
    d.gwetroot_frac,
    c.lat * (pi() / 180.0E0) AS phi,
    2.0E0 * pi() * CAST(EXTRACT(DOY FROM d.date) AS DOUBLE) / 365.0E0 AS b
  FROM fieldshift_gold.power_square_daily d
  JOIN fieldshift_gold.cells c
    ON c.power_key = d.power_key AND c.data_version = d.data_version
  WHERE d.data_version = '{data_version}'
),
sun AS (
  SELECT
    adj.*,
    1.0E0 + 0.033E0 * cos(b) AS dr,
    0.409E0 * sin(b - 1.39E0) AS decl,
    tmax_adj_c - tmin_adj_c AS trange_raw
  FROM adj
),
ws AS (
  SELECT
    sun.*,
    acos(CASE
           WHEN -tan(phi) * tan(decl) < -1.0E0 THEN -1.0E0
           WHEN -tan(phi) * tan(decl) > 1.0E0 THEN 1.0E0
           ELSE -tan(phi) * tan(decl)
         END) AS omega
  FROM sun
),
ra AS (
  SELECT
    ws.*,
    24.0E0 * 60.0E0 / pi() * 0.0820E0 * dr
      * (omega * sin(phi) * sin(decl) + cos(phi) * cos(decl) * sin(omega)) AS ra_mj
  FROM ws
)
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
  gwetroot_frac,
  0.0023E0 * 0.408E0 * ra_mj * (tmean_adj_c + 17.8E0)
    * sqrt(CASE WHEN trange_raw < 0.0E0 THEN 0.0E0 ELSE trange_raw END) AS et0_mm
FROM ra
