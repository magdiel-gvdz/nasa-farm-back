# Proposal

## Why

El entorno despliega hoy una función Lambda detrás de API Gateway, con un límite de 30 segundos por petición y sin respuestas en streaming. El backend necesita un proceso de larga vida (datos en memoria, chat por SSE), así que cada entorno pasa a ejecutar el contenedor en ECS Express Mode. App Runner, la opción original, está cerrado para esta cuenta.

## What Changes

- **BREAKING**: se eliminan la función Lambda, la API HTTP de API Gateway y sus registros; la URL de la API cambia.
- Cada entorno (`dev`, `pr-N`) crea un servicio de ECS Express Mode con la imagen de ECR indicada por `image_tag`.
- Tabla DynamoDB por entorno para geocercas y conversaciones.
- El rol de la API pasa de Lambda a tarea de ECS y recibe permisos sobre su tabla, su bucket y los recursos de solo lectura de DATA.
- El bucket por entorno se conserva (misma dirección de recurso en Terraform) y pasa a usarse para `uploads/` y `cache/`.
- Nuevas variables de entrada y salidas del stack.

## Capabilities

### New Capabilities
- `environment-infrastructure`: recursos de AWS que componen un entorno de la API (servicio, estado, almacenamiento, permisos) y su ciclo de vida.

### Modified Capabilities

Ninguna.

## Impact

- `infra/environment/main.tf`, `variables.tf`, `outputs.tf`, `tests/environments.tftest.hcl`, `dev.example.tfvars`.
- La salida `lambda_function_name` desaparece; `api_url` pasa a ser la URL del servicio.
- Este cambio no puede fusionarse solo: el workflow actual no publica imagen. Se integra en la misma rama y PR que `a4-deploy-pipeline`.
- Tarea del plan: **A3** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 1 (Plataforma).
- Depende de: `a2-bootstrap-ecs-permissions` aplicado.
- Estimación: 3.5 h.
