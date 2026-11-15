# Tasks

## 1. Malla

- [x] 1.1 Portar `grid.py` de DATA a `app/geo/grid.py` con las constantes EPSG:6933, 3856 × 1624 celdas, lado 9008.055210146 m, X0 = −17367530.44516138 e Y0 = 7314540.830638, y sus 7 pruebas a `tests/geo/test_grid.py`; verificar que las 7 pasan
- [x] 1.2 Añadir como dato de prueba el CSV de las 136 celdas de DATA y una prueba que recalcula `cell_id` desde cada centroide; verificar que coinciden las 136
- [x] 1.3 Añadir `pyproj` y `shapely` a las dependencias de ejecución y regenerar el bloqueo; verificar que la imagen Docker construye y arranca
  - Verificado en `pr-7`: la imagen construye y arranca en CI con pyproj 3.8.0 y shapely 2.2.0, y el servicio ECS asigna celdas

## 2. Geometría

- [x] 2.1 Implementar en `app/geo/geometry.py` la validación (tipo, anillos cerrados, rangos, vértices, autointersección) con mensajes es/en; verificar con pruebas de cada rechazo, incluida la pista de `[lon, lat]`
- [x] 2.2 Implementar área geodésica en hectáreas y centroide; verificar con el cuadrado de 1 km y con un `MultiPolygon` de dos partes

## 3. Localización

- [x] 3.1 Implementar `locate(geometry)` en `app/geo/locate.py`: valida, calcula área y centroide, obtiene la celda y consulta en el proveedor de datos si existe y a qué zona pertenece; verificar con pruebas de una geocerca por zona
- [x] 3.2 Implementar `out_of_region` con la lista de zonas en `details` y el límite de 10,000 ha; verificar con una geocerca en Nevada y otra sobredimensionada
- [x] 3.3 Sustituir la localización provisional de `/fields` por la real y añadir `cell_assignment` y `admin` a la respuesta; verificar con las pruebas de `/fields` y regenerar `contracts/openapi.json`
- [x] 3.4 Documentar en `docs/api-contract.md` la regla de celda dominante y el error `out_of_region`; verificar con una llamada `curl` al preview para un punto de Saltillo y otro fuera de región
