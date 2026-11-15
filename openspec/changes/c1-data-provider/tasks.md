# Tasks

## 1. Interfaz y modelos

- [x] 1.1 Convertir `app/data.py` en el paquete `app/data/` y definir en `models.py` las filas tipadas `Cell`, `Zone`, `ClimatologyDecade`, `IndicatorDecade`, `IndicatorYear`, `SoilLayer`, `Source` y `DailyRow` con los nombres y unidades de `docs/fuentes_de_datos.md` §8; verificar con una prueba que construye cada modelo con valores nulos permitidos
- [x] 1.2 Definir en `provider.py` el protocolo `DataProvider` (`is_ready`, `data_version`, `cells`, `zones`, `cell`, `climatology`, `indicators`, `years`, `soil`, `sources`, `daily`) y la excepción de celda desconocida; verificar con una prueba de conformidad reutilizable por cualquier implementación
- [x] 1.3 Añadir `data_provider` a `app/config.py` y una fábrica que falla con valor desconocido; verificar con pruebas del valor por defecto y de un valor inválido

## 2. Datos sintéticos

- [x] 2.1 Escribir `scripts/build_fixtures.py` que genera, con semilla fija, `app/data/fixtures/*.json` para dos celdas (Saltillo: heladas de noviembre a marzo; La Laguna: calor extremo y lluvia escasa), 2016-2025; verificar que dos ejecuciones producen archivos idénticos
- [x] 2.2 Implementar `FixtureProvider` leyendo esos archivos; `daily` devuelve una serie sintética coherente con los indicadores; verificar con la prueba de conformidad y con comprobaciones de 36 decenas y 10 años por celda
- [x] 2.3 Cuando DATA entregue su contrato v0, alinear nombres de columna y regenerar los archivos; verificar que la prueba de conformidad sigue pasando y anotar en el PR las columnas que cambiaron
  - Alineado con el contrato v1 (`docs/data_contract.md`): se añaden `windy_prob`, `wind_max_ms`, `windy_days`, `temp_adj_applied`, `n_days`, las columnas `_p05`/`_p95` del suelo, `valid_pixel_pct`, `low_coverage` y las de `v_cell_daily`

## 3. Integración en la API

- [x] 3.1 Conectar `GET /api/v1/sources` y `/ready` al proveedor y eliminar el lector del manifiesto, `manifest_key`, `data_lake_bucket` y sus pruebas; verificar con `pytest -q`
- [x] 3.2 Exponer el proveedor como dependencia inyectable de las rutas y sustituible en pruebas; verificar con una prueba que inyecta un proveedor no listo y obtiene `503` en `/ready`
- [x] 3.3 Documentar en `README.md` la variable `DATA_PROVIDER` y cómo regenerar los datos sintéticos; verificar que el comando documentado funciona
