# Proposal

## Why

El perfil y los motores necesitan los indicadores de DATA (gold), pero gold V0 no se publica hasta H15. Si cada pieza leyera Athena directamente, nadie podría avanzar ni probar hasta entonces. Una interfaz única de lectura con una implementación de datos sintéticos permite construir y probar todo sin AWS, y cambiar a los datos reales por configuración.

## What Changes

- Interfaz de lectura única para celdas, climatología por decena, indicadores por año y decena, series anuales, suelo, fuentes y serie diaria.
- Proveedor de datos sintéticos, determinista, con las mismas columnas y unidades que el contrato de DATA (`docs/fuentes_de_datos.md` §8 y §9) para al menos una celda de Saltillo y una de La Laguna.
- Selección por `DATA_PROVIDER` (`fixture` por defecto).
- `GET /api/v1/sources` y `/ready` pasan a leer del proveedor.
- **BREAKING**: se retira el manifiesto en S3 (`manifests/manifest.json`) y su lector.

## Capabilities

### New Capabilities
- `data-provider`: acceso de solo lectura a los datos agroclimáticos publicados por DATA, con independencia de dónde estén almacenados.

### Modified Capabilities

Ninguna.

## Impact

- `app/data.py` se convierte en el paquete `app/data/` (`provider.py`, `models.py`, `fixture.py`, `fixtures/`).
- `app/config.py`: se quitan `data_lake_bucket` y `manifest_key`, se añade `data_provider`.
- Pruebas actuales del manifiesto se sustituyen.
- De esta interfaz dependen `b4`, `c2`, `c3`, `c4`, `d2`, `d3` y `d4`: su firma se congela al fusionar.
- Tarea del plan: **C1** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 3 (Datos y perfil).
- Depende de: nada (el contrato v0 sintético de DATA llega en H8; ajustar columnas entonces).
- Estimación: 1.5 h.
