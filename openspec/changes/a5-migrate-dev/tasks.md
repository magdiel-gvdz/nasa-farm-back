# Tasks

## 1. Migración de dev

- [ ] 1.1 Fusionar el PR de contenedor y seguir el workflow de `main`; verificar que el apply elimina la función y la API HTTP, crea el servicio y que la prueba de humo pasa
- [ ] 1.2 Verificar a mano `curl <api_url>/health` y `curl <api_url>/docs`, y que `aws lambda list-functions` ya no lista `nasa-farm-dev-api`
- [ ] 1.3 Entregar la URL al frontend y actualizar la variable `API_CORS_ORIGINS` con `["*"]` por decisión explícita del usuario; verificar con una petición `OPTIONS` desde un origen externo que la respuesta incluye `access-control-allow-origin`

## 2. Retiro de permisos heredados

- [x] 2.1 Confirmar que no queda ningún preview abierto con Lambda (`aws lambda list-functions` sin funciones `nasa-farm-pr-*`); verificar con la salida del comando
- [x] 2.2 Quitar de `infra/bootstrap/main.tf` las sentencias de Lambda y API Gateway, sus registros y `lambda.amazonaws.com` de `iam:PassRole`, y actualizar el test; verificar con `terraform -chdir=infra/bootstrap test`
- [ ] 2.3 Aplicar el bootstrap con credenciales de administrador y relanzar el workflow de `dev`; verificar que el despliegue termina correctamente
