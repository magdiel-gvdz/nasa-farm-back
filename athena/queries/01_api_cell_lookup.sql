-- API: todas las celdas con su polígono (cargar una vez; resolver polígono -> celda en memoria).
SELECT cell_id, zone_id, zone_name, lat, lon, geometry_wkt, cell_elev_m, climate_shared_by_n_cells
FROM fieldshift_gold.v_cells
ORDER BY cell_id;
