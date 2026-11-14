# Proposal

## Why

Con la conversación solo en memoria, recargar la página o redesplegar el servicio borra el chat, y con dos instancias del servicio un mensaje puede llegar a la que no conoce la conversación. Además, para que el modelo mantenga el hilo entre turnos con herramientas hay que devolverle su propia respuesta anterior completa, no un resumen.

## What Changes

- Las conversaciones y sus turnos se guardan en la tabla DynamoDB del entorno.
- Se guarda el contenido completo de cada turno del asistente (texto, usos de herramienta, resultados y bloques de razonamiento) tal como lo devolvió el modelo.
- `GET /api/v1/chat/conversations/{id}` devuelve el historial visible para repintar el chat.
- Tope de turnos por conversación.

## Capabilities

### New Capabilities
- `chat-history`: persistencia y recuperación de las conversaciones del chat agrónomo.

### Modified Capabilities

Ninguna.

## Impact

- Nuevos: `app/store/conversations.py`, cambios en `app/agent/stream.py` (lectura y escritura del historial) y en `app/api/routes/chat.py`.
- Reutiliza el repositorio de `b3-fields-store` con claves `conv#` y `msg#`.
- Tarea del plan: **E3** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 2 (API y estado).
- Depende de: `e1-chat-streaming`, `b3-fields-store`.
- Estimación: 1.5 h.
