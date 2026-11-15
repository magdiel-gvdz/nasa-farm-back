# Proposal

## Why

Todo el producto parte de una geocerca: el agricultor marca su terreno, declara su rotación actual y a partir de ahí se calculan perfil, aptitud y rotaciones. Hace falta guardar esas geocercas por cliente y recuperarlas tras reiniciar el contenedor o recargar la página.

## What Changes

- CRUD real de `/api/v1/fields` sustituyendo las respuestas fijas.
- Persistencia en la tabla DynamoDB del entorno, separada por `X-Client-Id`; implementación en memoria para desarrollo local y pruebas.
- Cada geocerca guarda geometría, tipo (`field` o `greenhouse`), rotación actual, riego, ganado, datos de invernadero y la ubicación derivada (área, centroide, celda y zona).
- La ubicación se obtiene de un servicio de localización con interfaz fija; su implementación real llega en `b4-field-geolocation`.

## Capabilities

### New Capabilities
- `fields`: alta, consulta, edición y borrado de las geocercas e invernaderos de un cliente.

### Modified Capabilities

Ninguna.

## Impact

- Nuevos: `app/store/` (interfaz, memoria, DynamoDB), `app/api/routes/fields.py` real, `tests/store/`.
- Variable de entorno `APP_TABLE`; sin ella se usa memoria.
- La misma tabla y la misma interfaz se reutilizan para conversaciones en `e3-chat-history`.
- Tarea del plan: **B3** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 2 (API y estado).
- Depende de: `b1-api-contract`; la tabla real requiere `a3-environment-ecs-express`.
- Estimación: 2 h.
