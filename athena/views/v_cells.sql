-- Una fila por celda de 9 km. Para POST /v1/fields (polígono -> celda) y OUT_OF_REGION.
-- Filtra la data_version vigente por dentro; gold_build la recrea al publicar ({data_version} se sustituye).
CREATE OR REPLACE VIEW fieldshift_gold.v_cells AS
SELECT
  c.cell_id
, c.zone_id
, z.name zone_name
, c.lat
, c.lon
, c.geometry_wkt
, c.cell_elev_m
, c.cell_elev_source
, c.power_cell_lat
, c.power_cell_lon
, c.power_elev_m
, c.climate_shared_by_n_cells
, c.data_version
FROM
  (fieldshift_gold.cells c
INNER JOIN fieldshift_gold.zones z ON ((z.zone_id = c.zone_id) AND (z.data_version = c.data_version)))
WHERE (c.data_version = '{data_version}')
