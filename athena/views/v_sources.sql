-- Una fila por fuente de datos: atribuciones para GET /v1/sources.
-- Filtra la data_version vigente por dentro; gold_build la recrea al publicar ({data_version} se sustituye).
CREATE OR REPLACE VIEW fieldshift_gold.v_sources AS
SELECT
  source_id
, name
, organization
, product_version
, url
, resolution
, period
, access_date
, license
, data_class
, status
, used_for
, data_version
FROM
  fieldshift_gold.sources
WHERE (data_version = '{data_version}')
