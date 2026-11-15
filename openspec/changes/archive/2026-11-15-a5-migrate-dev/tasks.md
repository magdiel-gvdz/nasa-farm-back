# Tasks

## 1. Migración de dev

- [x] 1.1 Fusionar el PR de contenedor y seguir el workflow de `main`; verificar que el apply elimina la función y la API HTTP, crea el servicio y que la prueba de humo pasa
- [x] 1.2 Verificar a mano `curl <api_url>/health` y `curl <api_url>/docs`, y que `aws lambda list-functions` ya no lista `nasa-farm-dev-api`
- [x] 1.3 Entregar la URL al frontend y actualizar la variable `API_CORS_ORIGINS` con `["*"]` por decisión explícita del usuario; verificar con una petición `OPTIONS` desde un origen externo que la respuesta incluye `access-control-allow-origin`
  - Verificado el 15 de noviembre de 2026 tras fusionar el PR #7: el apply de `dev` destruyó `aws_lambda_function.api` y `aws_apigatewayv2_api.api`, creó el servicio ECS y pasó la prueba de humo. `/health` y `/docs` responden `200` en `https://na-80276c48174345cab83857032d88d2ac.ecs.us-east-1.on.aws` y el preflight `OPTIONS` desde un origen externo devuelve `access-control-allow-origin: *`. La ausencia de la función se comprobó en el registro de Terraform, no con `aws lambda list-functions`

## 2. Retiro de permisos heredados

- [x] 2.1 Confirmar que no queda ningún preview abierto con Lambda (`aws lambda list-functions` sin funciones `nasa-farm-pr-*`); verificar con la salida del comando
- [x] 2.2 Quitar de `infra/bootstrap/main.tf` las sentencias de Lambda y API Gateway, sus registros y `lambda.amazonaws.com` de `iam:PassRole`, y actualizar el test; verificar con `terraform -chdir=infra/bootstrap test`
- [x] 2.3 Aplicar el bootstrap con credenciales de administrador y relanzar el workflow de `dev`; verificar que el despliegue termina correctamente
  - Aplicado el 15 de noviembre de 2026 con credenciales de administrador (3 políticas cambiadas, ninguna creada ni destruida). `aws lambda list-functions` ya no lista funciones `nasa-farm-*` y el workflow de `dev` relanzado después terminó correctamente
