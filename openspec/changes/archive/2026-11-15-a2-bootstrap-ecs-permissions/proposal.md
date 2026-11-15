# Proposal

## Why

Los roles de despliegue de GitHub Actions y el límite de permisos de ejecución solo cubren Lambda, API Gateway y lectura de S3. Para desplegar el contenedor en ECS Express Mode y para que la API lea el lake de DATA, use DynamoDB y llame a Bedrock, el stack de bootstrap tiene que ampliarse antes que cualquier otro cambio de infraestructura.

## What Changes

- Repositorio ECR privado y compartido por todos los entornos, con etiquetas inmutables.
- Los roles de despliegue (`dev` y `preview`) pueden publicar imágenes, gestionar su servicio de ECS Express Mode, su tabla DynamoDB y los tres roles IAM del servicio, siempre acotados por el patrón de nombres de su entorno.
- El límite de permisos del rol de ejecución de la API se amplía a: tabla propia, bucket propio, lectura del lake y de Athena de DATA (misma cuenta, región us-west-2), parámetro SSM de versión de datos y Bedrock.
- Se conservan temporalmente los permisos de Lambda y API Gateway para que Terraform pueda destruir esos recursos al migrar (se retiran en `a5-migrate-dev`).
- Requiere un `terraform apply` manual del bootstrap con credenciales de administrador.

## Capabilities

### New Capabilities
- `deploy-permissions`: identidades y permisos con los que CI despliega cada entorno y con los que la API se ejecuta.

### Modified Capabilities

Ninguna.

## Impact

- `infra/bootstrap/main.tf`, `variables.tf`, `outputs.tf`, `tests/identity.tftest.hcl`, `bootstrap.example.tfvars`.
- Nuevas variables de repositorio en GitHub: `ECR_REPOSITORY_URL`.
- Ninguna parte de la aplicación cambia.
- Tarea del plan: **A2** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 1 (Plataforma).
- Depende de: prueba manual de ECS Express Mode en la cuenta (P1 del plan).
- Estimación: 2 h.
