# Design

## Context

El bootstrap se aplica a mano con credenciales de administrador y su estado vive en el bucket de estado. Crea dos roles de despliegue (dev y preview) restringidos por patrón de nombres (`nasa-farm-dev`, `nasa-farm-pr-*`) y un límite de permisos (`runtime_boundary`) que CI no puede quitar de los roles que crea. Lake y API viven en la misma cuenta; el lake está en us-west-2 y el backend en us-east-1.

## Goals / Non-Goals

**Goals:**
- Que CI pueda crear y destruir un servicio de ECS Express Mode por entorno sin permisos de administrador.
- Que un PR malicioso o equivocado no pueda dar a la API más permisos que los del límite.

**Non-Goals:**
- Crear el servicio, la tabla o los roles del entorno (eso es `a3-environment-ecs-express`).
- Crear el lake, el workgroup o las vistas de Athena (son de DATA).

## Decisions

- **Un solo repositorio ECR en bootstrap, no uno por entorno.** Las imágenes se etiquetan con el SHA del commit; un preview y dev pueden compartir capas. Alternativa descartada: ECR por entorno, que alarga cada preview y obliga a borrar imágenes al destruir.
- **Tres roles por entorno, con nombres fijos:** `<entorno>-api` (rol de tarea, el que ya existe para Lambda cambia de principal), `<entorno>-api-exec` (rol de ejecución) y `<entorno>-api-infra` (rol de infraestructura de Express Mode). El rol de despliegue solo puede crear roles con esos nombres.
- **El rol de tarea mantiene el límite de permisos.** Los roles de ejecución y de infraestructura no llevan límite, pero el rol de despliegue solo puede adjuntarles las políticas administradas de AWS previstas para ese uso (condición `iam:PolicyARN`) y no puede ponerles políticas en línea. Los nombres exactos de las políticas administradas se confirman en la documentación de ECS Express Mode al implementar.
- **`iam:PassRole` condicionado por servicio** (`ecs-tasks.amazonaws.com` y `ecs.amazonaws.com`), además de `lambda.amazonaws.com` mientras dure la transición.
- **Recursos de DATA por nombre, parametrizados:** bucket del lake, bucket de resultados de Athena, workgroup, base de Glue y prefijo SSM entran como variables con los valores del documento de DATA por defecto (`fieldshift-lake-<cuenta>`, `fieldshift-athena-results-<cuenta>`, `fieldshift`, `fieldshift_gold`, `/fieldshift/`). El límite permite lectura del lake solo bajo `gold/`.
- **Bedrock:** el límite permite `bedrock:InvokeModel` e `InvokeModelWithResponseStream`; el recurso se acota a modelos de Anthropic.

## Risks / Trade-offs

- [El recurso de Express Mode necesita acciones IAM que no anticipamos] → Aplicar primero en un preview; el error de acceso denegado nombra la acción que falta. Ampliar el bootstrap y volver a aplicar.
- [Solo una persona tiene credenciales de administrador] → Esta tarea es la primera del carril; el resto del equipo trabaja en local mientras tanto.
- [Los nombres de los recursos de DATA cambian] → Son variables; se corrige con otro apply del bootstrap.

## Migration Plan

1. Aplicar el bootstrap ampliado (conserva permisos de Lambda y API Gateway).
2. Registrar `ECR_REPOSITORY_URL` como variable del repositorio en GitHub.
3. Tras migrar dev (`a5-migrate-dev`), quitar los permisos heredados con un segundo apply.

Vuelta atrás: aplicar el commit anterior del bootstrap; ningún recurso de entorno depende todavía de lo nuevo.
