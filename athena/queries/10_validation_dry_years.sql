-- Validación: lluvia anual por zona y año, del año más seco al más lluvioso.
-- Sirve para contrastar con sequías conocidas (por ejemplo 2020-2022 en el norte de México).
SELECT zone_id, year, round(avg(precip_mm)) AS precip_mm, round(avg(et0_mm)) AS et0_mm,
       round(avg(dry_spell_max_d)) AS dry_spell_max_d, round(avg(ws_days)) AS ws_days
FROM fieldshift_gold.v_cell_year
GROUP BY zone_id, year
ORDER BY zone_id, precip_mm;
