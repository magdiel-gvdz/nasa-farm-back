# Proposal

## Why

El workflow de despliegue empaqueta un ZIP de Lambda y lo entrega a Terraform. Con el servicio de contenedor, el pipeline tiene que construir la imagen, publicarla en ECR y pasar su etiqueta a Terraform; y la aplicación ya no necesita el adaptador de Lambda.

## What Changes

- El workflow construye y publica la imagen etiquetada con el SHA del commit antes de `terraform apply`.
- Terraform recibe `image_tag` y `ecr_repository_url`; la prueba de humo consulta la nueva URL.
- La destrucción de previews y el workflow manual de limpieza funcionan con los recursos nuevos.
- **BREAKING**: se retiran Mangum, `scripts/package_lambda.py` y sus pruebas; la aplicación deja de exportar `handler`.
- Se mantienen las reglas actuales: sin despliegue para forks ni borradores, sin cancelar un apply en curso.

## Capabilities

### New Capabilities
- `deploy-pipeline`: cómo un commit llega a un entorno (construcción, publicación, aplicación, verificación y limpieza).

### Modified Capabilities

Ninguna.

## Impact

- `.github/workflows/infrastructure.yml`, `cleanup-preview.yml`, `check.yml`.
- `app/main.py`, `tests/test_api.py`, `pyproject.toml`, `requirements.txt`; se eliminan `scripts/package_lambda.py` y `tests/test_package_lambda.py`.
- Se integra en la misma rama y PR que `a3-environment-ecs-express`.
- Tarea del plan: **A4** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 1 (Plataforma).
- Depende de: `a1-docker-image`, `a3-environment-ecs-express`.
- Estimación: 1.5 h.
