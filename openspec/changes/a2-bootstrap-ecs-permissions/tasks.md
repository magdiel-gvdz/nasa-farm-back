# Tasks

## 1. Repositorio de imágenes

- [x] 1.1 Agregar a `infra/bootstrap/main.tf` el repositorio ECR `${project}-api` con etiquetas inmutables, escaneo al publicar y regla de ciclo de vida (conservar las últimas 30 imágenes); exponer `ecr_repository_url` en `outputs.tf`; verificar con una aserción nueva en `tests/identity.tftest.hcl`
- [x] 1.2 Dar a ambos roles de despliegue `ecr:GetAuthorizationToken` y las acciones de publicación y lectura solo sobre ese repositorio; verificar con aserción en el test de Terraform

## 2. Permisos de despliegue

- [x] 2.1 Agregar variables `data_region`, `data_lake_bucket`, `athena_results_bucket`, `athena_workgroup`, `glue_database` y `data_version_parameter_prefix` con los valores del documento de DATA por defecto; actualizar `bootstrap.example.tfvars`; verificar con `terraform validate`
- [x] 2.2 Añadir al rol de despliegue las acciones de ECS para servicios Express Mode, clúster y definiciones de tarea, y las de DynamoDB sobre `table/${name_pattern}-app`; verificar con el test de Terraform que el recurso está acotado por patrón de nombre
- [x] 2.3 Extender los permisos IAM del rol de despliegue a los roles `-api`, `-api-exec` y `-api-infra`: creación de `-api` solo con límite, `iam:AttachRolePolicy` condicionado por `iam:PolicyARN` para los otros dos, y `iam:PassRole` condicionado a `ecs-tasks.amazonaws.com`, `ecs.amazonaws.com` y `lambda.amazonaws.com`; confirmar en la documentación de ECS Express Mode los nombres de las políticas administradas; verificar con aserciones del test
- [x] 2.4 Mantener sin cambios las sentencias de Lambda, API Gateway y sus registros; verificar con una aserción que siguen presentes

## 3. Límite de permisos de ejecución

- [x] 3.1 Ampliar `runtime_boundary` con DynamoDB (tabla propia), S3 del entorno (`uploads/*` y `cache/*` lectura y escritura), lectura de `gold/*` del lake, Athena (workgroup de DATA), bucket de resultados, Glue (base de DATA), SSM (prefijo de DATA), Bedrock y registros de ECS; verificar con aserciones del test que no incluye acciones `iam:*` ni escritura en el lake
- [x] 3.2 Ejecutar `terraform fmt -check -recursive infra`, `terraform -chdir=infra/bootstrap validate` y `terraform -chdir=infra/bootstrap test`; verificar que todo pasa sin credenciales

## 4. Aplicación

- [ ] 4.1 Con credenciales de administrador, ejecutar `plan` y `apply` del bootstrap contra el estado remoto; verificar que el plan no destruye el bucket de estado ni el proveedor OIDC y que `terraform output ecr_repository_url` devuelve un valor
- [ ] 4.2 Registrar la variable de repositorio `ECR_REPOSITORY_URL` en GitHub; verificar con `gh variable list`
- [x] 4.3 Documentar en `README.md` las variables nuevas del bootstrap y la variable de GitHub; verificar que la tabla de variables del README coincide con `variables.tf`
