# Tasks

## 1. Variables y salidas

- [x] 1.1 En `variables.tf`: añadir `image_tag`, `ecr_repository_url`, `data_provider` (por defecto `fixture`, validado a `fixture|athena`), `data_region`, `data_lake_bucket`, `athena_results_bucket`, `athena_workgroup`, `athena_database`, `data_version_parameter` y `bedrock_model_id`; quitar `lambda_zip_path`; verificar con `terraform validate`
- [x] 1.2 En `outputs.tf`: `api_url` desde el servicio, añadir `app_table` y `service_arn`, quitar `lambda_function_name`; actualizar `dev.example.tfvars`; verificar con `terraform validate`

## 2. Servicio y roles

- [x] 2.1 Eliminar de `main.tf` Lambda, API Gateway, su permiso y sus grupos de registros; verificar que `terraform validate` pasa y que el plan de prueba no contiene esos tipos de recurso
- [x] 2.2 Cambiar el principal de confianza del rol `-api` a `ecs-tasks.amazonaws.com` conservando nombre y límite de permisos, y reescribir su política: tabla propia, `uploads/*` y `cache/*` del bucket, y lectura de DATA (lake `gold/*`, Athena, resultados, Glue, SSM) y Bedrock; verificar con aserciones en `tests/environments.tftest.hcl`
- [x] 2.3 Crear los roles `-api-exec` y `-api-infra` con las políticas administradas confirmadas en `a2-bootstrap-ecs-permissions`; verificar con aserción que no tienen políticas en línea
- [x] 2.4 Crear `aws_ecs_express_gateway_service` con nombre `${local.name}-api`, imagen `${ecr_repository_url}:${image_tag}`, puerto 8080, `health_check_path = "/health"`, 1 vCPU, 2 GB, escalado mínimo 1 y máximo 1 (preview) o 2 (dev), `wait_for_steady_state = true` y las variables de entorno listadas en el diseño; verificar con aserciones del test sobre imagen, puerto y variables

## 3. Estado

- [x] 3.1 Crear la tabla DynamoDB `${local.name}-app` (`client_id`, `sk`, pago por petición, protección contra borrado solo fuera de previews); verificar con aserciones para `dev` y para `pr-7`
- [x] 3.2 Confirmar que el bucket conserva la dirección `aws_s3_bucket.data_lake` y su configuración; verificar que el test existente del bucket sigue pasando sin cambios

## 4. Verificación

- [x] 4.1 Reescribir `tests/environments.tftest.hcl` para el nuevo conjunto de recursos y ejecutar `terraform fmt -check -recursive infra`, `validate` y `test`; verificar que todo pasa sin credenciales
- [ ] 4.2 Aplicar en un preview real a través del PR conjunto con `a4-deploy-pipeline` y verificar que `curl <api_url>/health` responde `200`; anotar en el PR el tiempo de creación y el atributo de `ingress_paths` usado para la URL
- [ ] 4.3 Si Express Mode no puede crearse en la cuenta tras una hora de intentos, registrar el error en el PR y cambiar a Fargate + ALB en la VPC por defecto manteniendo variables y salidas; verificar con el mismo `curl`
