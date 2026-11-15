-- Calidad: conteos esperados y claves únicas de las vistas (debe devolver dup = 0 en todas).
SELECT 'v_cells' AS view_name, count(*) AS n_rows, count(*) - count(DISTINCT cell_id) AS dup
FROM fieldshift_gold.v_cells
UNION ALL
SELECT 'v_cell_profile', count(*), count(*) - count(DISTINCT cell_id || '-' || cast(decade AS varchar))
FROM fieldshift_gold.v_cell_profile
UNION ALL
SELECT 'v_cell_indicators', count(*),
       count(*) - count(DISTINCT cell_id || '-' || cast(year AS varchar) || '-' || cast(decade AS varchar))
FROM fieldshift_gold.v_cell_indicators
UNION ALL
SELECT 'v_cell_year', count(*), count(*) - count(DISTINCT cell_id || '-' || cast(year AS varchar))
FROM fieldshift_gold.v_cell_year
UNION ALL
SELECT 'v_cell_soil', count(*), count(*) - count(DISTINCT cell_id || '-' || depth_cm)
FROM fieldshift_gold.v_cell_soil
UNION ALL
SELECT 'v_cell_daily', count(*), count(*) - count(DISTINCT cell_id || '-' || cast(date AS varchar))
FROM fieldshift_gold.v_cell_daily
UNION ALL
SELECT 'v_sources', count(*), count(*) - count(DISTINCT source_id)
FROM fieldshift_gold.v_sources
ORDER BY 1;
