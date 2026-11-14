# Proposal

## Why

Cuatro personas fusionan cambios en paralelo y cada merge despliega `dev`, que es el entorno de la demo. La prueba de humo actual solo consulta `/health`. Hace falta una comprobación del recorrido completo del usuario que cualquiera pueda lanzar contra un preview antes de fusionar y contra `dev` después de cada publicación de datos.

## What Changes

- Script que recorre contra una URL: catálogo, fuentes, alta de geocerca, perfil, aptitud (detalle y matriz), rotaciones, escenario y borrado.
- Valida cada respuesta contra `contracts/openapi.json` y distingue entre respuesta fija y respuesta real.
- Paso opcional en el workflow de despliegue.
- Herramienta de verificación, sin cambio de comportamiento de la API (`skip_specs`).

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

Ninguna.

## Impact

- Nuevos: `scripts/smoke_e2e.py`, `docs/smoke.md`; cambio en `.github/workflows/infrastructure.yml`.
- Crea y borra una geocerca con un `X-Client-Id` propio en cada ejecución.
- Tarea del plan: **G1** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 2 (API y estado).
- Depende de: `b1-api-contract`.
- Estimación: 1.5 h.
