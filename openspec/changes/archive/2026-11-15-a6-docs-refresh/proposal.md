# Proposal

## Why

`README.md` y `openspec/config.yaml` describen una API sobre Lambda, Mangum y API Gateway con un manifiesto en S3. Tras la migración, quien lea esos archivos (personas y agentes de código que usan el contexto de OpenSpec) trabajaría con una imagen falsa del sistema.

## What Changes

- `README.md` describe la arquitectura de contenedor, el flujo de imagen, las variables nuevas y el desarrollo local con Docker.
- `openspec/config.yaml` actualiza el contexto del proyecto (stack, validación y alcance).
- Se elimina `contracts/data-manifest.schema.json` si ya nadie lo usa.
- Sin cambios de comportamiento: este cambio no lleva especificaciones (`skip_specs`).

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

Ninguna.

## Impact

- Solo documentación y configuración de OpenSpec.
- Tarea del plan: **A6** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 1 (Plataforma).
- Depende de: `a5-migrate-dev`.
- Estimación: 0.5 h.
