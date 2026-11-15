# Proposal

## Why

Los datos reales los publica DATA como vistas de Athena en `fieldshift_gold`. Una consulta de Athena tarda entre uno y tres segundos, demasiado para los controles interactivos de escenarios; pero el conjunto completo es pequeño (136 celdas). Cargarlo entero en memoria al arrancar da respuestas inmediatas y, al vigilar la versión publicada, evita servir datos anteriores tras cada publicación de DATA.

## What Changes

- Proveedor `athena` que lee las seis vistas `v_*` completas a memoria al arrancar.
- Recarga automática cuando cambia el parámetro SSM `/fieldshift/data_version` (se revisa cada 5 minutos).
- Si una recarga falla, se conserva la última copia buena; si nunca hubo carga, la API informa `data_unavailable`.
- Validación de las columnas mínimas de cada vista antes de aceptar una carga.
- Lectura entre regiones: la API está en us-east-1 y los datos en us-west-2 (misma cuenta).

## Capabilities

### New Capabilities
- `data-provider`: acceso de solo lectura a los datos agroclimáticos publicados por DATA, con independencia de dónde estén almacenados.

### Modified Capabilities

Ninguna.

## Impact

- Nuevo: `app/data/athena.py`, pruebas con un ejecutor de consultas simulado.
- Dependencia de ejecución nueva: `awswrangler` (trae `pandas` y `pyarrow`, que también usan los motores).
- Variables: `DATA_REGION`, `ATHENA_WORKGROUP`, `ATHENA_DATABASE`, `DATA_VERSION_PARAMETER`.
- Activar en `dev` requiere cambiar `DATA_PROVIDER` a `athena` en las variables del repositorio.
- Tarea del plan: **C2** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 3 (Datos y perfil).
- Depende de: `c1-data-provider`, `a3-environment-ecs-express`, gold V0 publicado por DATA (H15).
- Estimación: 2.5 h.

## Condiciones para activar

La carga usa seis vistas en memoria; `v_cell_daily` se permite bajo demanda en C4. Se ejecutan SELECT sin CTAS, UNLOAD ni reutilización. SSM `none` no es una publicación. La activación requiere datos publicados y un protocolo de consistencia acordado, implementado y probado con DATA durante la recreación de vistas; el Terraform de referencia no garantiza por sí solo esa consistencia.
