# Proposal

## Why

Cuatro personas de backend y el equipo de frontend necesitan trabajar a la vez. Eso solo es posible si la forma exacta de cada petición y respuesta queda fijada primero. Este cambio publica el contrato completo del MVP con respuestas fijas, de modo que el frontend integra desde el primer preview y cada endpoint se sustituye después por su implementación real sin cambiar de forma.

## What Changes

- Todos los endpoints de negocio viven bajo `/api/v1` con claves JSON en `snake_case`.
- Modelos de petición y respuesta para: cultivos, fuentes, geocercas, perfil, aptitud y rotaciones.
- Cada endpoint sin implementación real devuelve una respuesta fija válida (celda de Saltillo) marcada con el encabezado `X-Fieldshift-Mock: 1`.
- `contracts/openapi.json` versionado y comprobado en CI.
- **BREAKING**: `GET /v1/sources` pasa a `GET /api/v1/sources`.
- Diferencias respecto a `docs/backend-handoff.md` §6, ya decididas en el plan: calendario de riesgos en 36 decenas, perfil síncrono, secciones sin dato en `null`, `erosion_exposure_index` en lugar de `erosion_t_ha_per_year`, y el error `OUT_OF_REGION`.

## Capabilities

### New Capabilities
- `api-contract`: superficie HTTP pública de la API (rutas, esquemas y versionado) que consumen el frontend y el chat.

### Modified Capabilities

Ninguna.

## Impact

- Nuevos: `app/api/` (rutas por recurso), `app/api/schemas/`, `app/api/fixtures/*.json`, `contracts/openapi.json`, `scripts/export_openapi.py`, `tests/api/`.
- Modificado: `app/main.py` (registro de rutas).
- Los cambios `b2`, `b3`, `c3`, `d1`, `d2` y `d3` dependen de estos modelos; no deben renombrar ni quitar campos sin avisar al frontend.
- Tarea del plan: **B1** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 2 (API y estado).
- Depende de: acuerdo con frontend sobre las diferencias de contrato (P4 del plan).
- Estimación: 2 h.
