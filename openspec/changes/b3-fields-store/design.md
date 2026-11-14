# Design

## Context

La tabla por entorno tiene clave de partición `client_id` y clave de orden `sk`, ambas cadenas. No hay inicio de sesión: el frontend genera un UUID y lo envía en `X-Client-Id`. Varias personas desarrollan en local sin credenciales de AWS.

## Goals / Non-Goals

**Goals:**
- Que las rutas no sepan dónde se guarda nada.
- Que local y pruebas funcionen sin AWS.

**Non-Goals:**
- Autenticación real, compartir geocercas entre clientes o historial de versiones.

## Decisions

- **Interfaz de repositorio con dos implementaciones** (memoria y DynamoDB) elegidas por configuración: si `APP_TABLE` está vacío se usa memoria. Una misma batería de pruebas se ejecuta contra ambas (DynamoDB simulado en pruebas).
- **Diseño de tabla única:** geocercas con `sk = "field#<id>"`. Listar es una consulta por `client_id` con prefijo `field#`. Las conversaciones usarán `conv#<id>` y `msg#<conv>#<n>` sin cambios de esquema.
- **Identificadores** `fld_` + ULID, generados en el servidor; ordenables por fecha de creación.
- **Elemento = documento:** el cuerpo de la geocerca se guarda como un solo atributo JSON más atributos de primer nivel para `cell_id`, `kind` y `created_at`. Evita mapear cada campo y tolera campos nuevos.
- **Localización inyectada:** la ruta llama a `locate(geometry)` que devuelve área, centroide, celda y zona, o lanza `OUT_OF_REGION`. Mientras no exista `b4`, una implementación provisional devuelve la celda de Saltillo de las respuestas fijas.
- **Tope de 50 geocercas por cliente** para acotar el coste de un cliente abusivo; se informa con `409`.

## Risks / Trade-offs

- [Cualquiera que conozca un `X-Client-Id` ve esas geocercas] → Aceptado para el hackathon; se declara en la documentación. No se guardan datos personales.
- [Elementos de más de 400 KB por geometrías enormes] → La validación de `b4` limita los vértices.
