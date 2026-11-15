# Proposal

## Why

`dev` es el entorno de la demo y hoy ejecuta la Lambda `nasa-farm-dev-api`. Una vez probado el contenedor en un preview hay que migrar `dev`, entregar la nueva URL al frontend y retirar los permisos de Lambda y API Gateway que el bootstrap conservó solo para la transición.

## What Changes

- Se fusiona el PR de `a3-environment-ecs-express` + `a4-deploy-pipeline`; el apply de `dev` sustituye Lambda y API Gateway por el servicio de contenedor.
- Se entrega la URL de `dev` al equipo de frontend (`VITE_API_URL`) y se actualiza `API_CORS_ORIGINS`.
- Se eliminan del bootstrap los permisos de Lambda y API Gateway, con un segundo apply manual.

## Capabilities

### New Capabilities
- `deploy-permissions`: identidades y permisos con los que CI despliega cada entorno y con los que la API se ejecuta.

### Modified Capabilities

Ninguna.

## Impact

- Entorno `dev` en AWS; `infra/bootstrap/main.tf` y su test.
- La URL anterior de API Gateway deja de responder.
- Tarea del plan: **A5** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 1 (Plataforma).
- Depende de: `a4-deploy-pipeline` verificado en un preview.
- Estimación: 0.5 h.
