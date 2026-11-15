-- Validación: las heladas deben aumentar con la altura de la celda (efecto de la corrección por altura).
SELECT c.zone_id,
       CASE WHEN c.cell_elev_m < 1000 THEN '1) < 1000 m' WHEN c.cell_elev_m < 1500 THEN '2) 1000-1500 m'
            WHEN c.cell_elev_m < 2000 THEN '3) 1500-2000 m' ELSE '4) >= 2000 m' END AS elevation_band,
       count(DISTINCT c.cell_id) AS cells,
       round(avg(y.frost_days), 1) AS frost_days_per_year,
       round(avg(y.hot_days_35), 1) AS hot_days_35_per_year
FROM fieldshift_gold.v_cells c
JOIN fieldshift_gold.v_cell_year y ON y.cell_id = c.cell_id
GROUP BY 1, 2
ORDER BY 1, 2;
