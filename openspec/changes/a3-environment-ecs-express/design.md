# Design

## Context

`infra/environment` es un stack único reutilizado por `dev` y por cada `pr-N`, con estado separado por entorno. El proveedor AWS fijado es 6.73.0 e incluye `aws_ecs_express_gateway_service` (comprobado en el esquema del proveedor instalado). Argumentos obligatorios: `execution_role_arn`, `infrastructure_role_arn` y `primary_container.image`. Opcionales relevantes: `service_name`, `cluster`, `cpu`, `memory`, `health_check_path`, `task_role_arn`, `scaling_target`, `network_configuration`, `wait_for_steady_state`, y dentro de `primary_container`: `container_port`, `environment`, `secret`, `aws_logs_configuration`. La URL pública se obtiene del atributo calculado `ingress_paths`.

## Goals / Non-Goals

**Goals:**
- Un `terraform apply` por entorno deja la API accesible por HTTPS con la imagen indicada.
- Un `terraform destroy` de un preview no deja recursos facturables.

**Non-Goals:**
- Dominio propio, WAF o VPC dedicada.
- Autoescalado por carga: una tarea basta para la demo.

## Decisions

- **ECS Express Mode en lugar de Fargate + ALB clásico.** Un recurso sustituye a clúster, definición de tarea, servicio, balanceador, grupo de destino, certificado y grupos de seguridad. Alternativa de respaldo si Express Mode falla en la cuenta: Fargate + ALB en la VPC por defecto, con la misma imagen y las mismas variables.
- **Red y clúster por defecto.** Sin `network_configuration` ni `cluster`: Express Mode usa la VPC por defecto y el clúster `default`. Evita NAT y subredes propias.
- **Tamaño:** 1 vCPU y 2 GB (pandas y los datos de gold en memoria caben con holgura). `scaling_target` con mínimo 1; máximo 1 en previews y 2 en dev.
- **`wait_for_steady_state = true`** para que el apply falle si el contenedor no pasa la comprobación de salud, y la prueba de humo del workflow no corra contra un servicio a medio desplegar.
- **Tres roles:** `-api` (tarea, con límite de permisos; mismo nombre que el rol actual, cambia el principal de confianza a `ecs-tasks.amazonaws.com`), `-api-exec` (ejecución: descarga de imagen y registros) y `-api-infra` (infraestructura de Express Mode), los dos últimos con políticas administradas de AWS.
- **Tabla única** `${name}-app` con clave de partición `client_id` y clave de orden `sk` (cadenas), facturación por petición. En previews se destruye con el entorno; en dev lleva protección contra borrado.
- **El bucket no cambia de dirección de recurso** (`aws_s3_bucket.data_lake`), para que Terraform no lo recree ni pierda objetos. Solo cambian los prefijos permitidos al rol.
- **Variables de entorno del contenedor** definidas aquí, aunque el código que las lee llegue en otros cambios: `ENVIRONMENT`, `CORS_ORIGINS`, `APP_TABLE`, `APP_BUCKET`, `DATA_PROVIDER`, `DATA_REGION`, `ATHENA_WORKGROUP`, `ATHENA_DATABASE`, `DATA_VERSION_PARAMETER`, `BEDROCK_MODEL_ID`, `CHAT_ENABLED`.
- **`DATA_PROVIDER` por variable de Terraform** con valor por defecto `fixture`; se cambia a `athena` cuando DATA publique gold V0, sin tocar código.

## Risks / Trade-offs

- [El balanceador administrado corta conexiones inactivas a los 60 s y Express Mode no expone ese ajuste] → El chat envía latidos SSE (requisito en `e1-chat-streaming`); no se resuelve aquí.
- [Crear un servicio tarda varios minutos y encarece cada preview] → Los PR se abren como borrador; el workflow no despliega borradores.
- [El coste no escala a cero] → Unos 2-3 USD al día por entorno; los previews se destruyen al cerrar el PR.
- [El cambio de principal del rol `-api` falla si Lambda aún lo usa] → `depends_on` y orden de destrucción: primero se elimina la función, después se actualiza el rol.

## Migration Plan

1. Probar en un preview (`pr-N`): el apply crea el servicio desde cero.
2. Al fusionar, el apply de `dev` destruye Lambda y API Gateway y crea el servicio (ver `a5-migrate-dev`).

Vuelta atrás: revertir el PR; el apply recrea Lambda y API Gateway (los permisos de transición siguen en el bootstrap).

## Open Questions

- Atributo exacto de `ingress_paths` que contiene la URL pública: se confirma con el primer apply en un preview.

## Permisos de DATA

El stack del entorno concederá al rol `-api` permisos equivalentes a `fieldshift-gold-read` mediante su política acotada a los recursos configurados; el bootstrap permitirá esas mismas operaciones en la boundary. Se conserva así la estrategia de política del rol de la tarea 2.2 sin requerir un attachment adicional. Verificar el acceso desde el rol real: ampliar solo la boundary no concede permisos. El bucket del entorno, aunque conserve la dirección `aws_s3_bucket.data_lake`, no es el lake compartido de DATA.
