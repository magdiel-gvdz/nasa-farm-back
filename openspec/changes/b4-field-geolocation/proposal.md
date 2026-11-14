# Proposal

## Why

Los datos de DATA están por celda de 9 km (EASE-Grid 2.0), no por parcela. Para responder cualquier cosa sobre una geocerca, la API tiene que convertir el polígono dibujado en la misma celda que usa el pipeline de DATA, y decir con claridad cuándo el terreno cae fuera de las cuatro zonas piloto.

## What Changes

- Validación de geometrías GeoJSON (`Polygon` y `MultiPolygon` en WGS84).
- Cálculo de área en hectáreas y centroide.
- Asignación de celda con las constantes exactas de la malla de DATA; celda dominante = la que contiene el centroide.
- Error `out_of_region` cuando la celda no pertenece a ninguna zona publicada, con la lista de zonas disponibles.
- Sustituye la localización provisional de `b3-fields-store`.

## Capabilities

### New Capabilities
- `field-geolocation`: validación de la geometría de una geocerca y su correspondencia con la malla de análisis y las zonas cubiertas.

### Modified Capabilities

Ninguna.

## Impact

- Nuevos: `app/geo/` (`grid.py`, `geometry.py`, `locate.py`), `tests/geo/`.
- Dependencias nuevas de ejecución: `pyproj` y `shapely`.
- Usa el proveedor de datos para saber qué celdas existen; hasta `c1-data-provider` se prueba con una lista fija.
- Tarea del plan: **B4** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 2 (API y estado).
- Depende de: `b1-api-contract`; código y CSV de celdas de DATA (P6 del plan).
- Estimación: 2 h.
