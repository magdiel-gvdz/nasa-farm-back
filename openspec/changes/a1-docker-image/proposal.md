# Proposal

## Why

La API se empaqueta hoy como ZIP para AWS Lambda. El backend pasa a ejecutarse como contenedor en ECS Express Mode (App Runner no está disponible en la cuenta), así que hace falta una imagen Docker que arranque la API sin depender de Lambda. Es el primer paso y no bloquea a nadie: la Lambda sigue desplegándose hasta `a4-deploy-pipeline`.

## What Changes

- Se agrega un `Dockerfile` y un `.dockerignore` en la raíz del repositorio.
- La imagen arranca la API con uvicorn en el puerto 8080, como usuario sin privilegios.
- `uvicorn` pasa a ser dependencia de ejecución (hoy solo es de desarrollo).
- Las comprobaciones de CI construyen la imagen, la arrancan y consultan `/health`.
- **No** se retira todavía Mangum ni `scripts/package_lambda.py`: el despliegue actual los usa hasta que cambie el pipeline.

## Capabilities

### New Capabilities
- `container-runtime`: cómo se empaqueta, configura y arranca la API como contenedor, con independencia de la plataforma que lo ejecute.

### Modified Capabilities

Ninguna.

## Impact

- Archivos nuevos: `Dockerfile`, `.dockerignore`.
- Archivos modificados: `requirements.txt`, `pyproject.toml`, `.github/workflows/check.yml`.
- Docker no está en el PATH de la máquina de desarrollo principal; la imagen puede validarse solo en CI.
- Tarea del plan: **A1** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 1 (Plataforma).
- Depende de: nada.
- Estimación: 1 h.
