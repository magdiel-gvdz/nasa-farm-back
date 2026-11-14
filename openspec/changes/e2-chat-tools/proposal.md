# Proposal

## Why

Un modelo de lenguaje sin acceso a datos inventa cifras, y en agronomía una cifra inventada es un daño real. Ambos documentos de diseño exigen que el motor sea explicable y que cada número tenga fuente. La solución es que el asistente no sepa nada por sí mismo: solo puede consultar el perfil y los motores ya construidos mediante herramientas, y citar lo que devuelven.

## What Changes

- Siete herramientas a disposición del asistente: listar geocercas, leer secciones del perfil, leer el calendario de riesgos, evaluar un cultivo, obtener la matriz de aptitud, comparar rotaciones y listar cultivos.
- Bucle de uso de herramientas dentro del flujo de eventos: eventos `tool` al empezar y terminar, `card` con el resultado cuando el frontend sabe pintarlo, y `citation` por cada fuente usada.
- Las herramientas solo acceden a los datos del cliente que conversa.

## Capabilities

### New Capabilities
- `chat-tools`: herramientas con las que el asistente consulta datos y motores de Field Shift durante una conversación.

### Modified Capabilities

Ninguna.

## Impact

- Nuevos: `app/agent/tools/` (una herramienta por archivo y un registro), cambios en `app/agent/stream.py` para el bucle.
- Reutiliza `app/profile`, `app/engines` y `app/store`; no duplica lógica.
- Tarea del plan: **E2** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 2 (API y estado).
- Depende de: `e1-chat-streaming`, `c3-field-profile`, `d2-crop-suitability`, `d3-rotation-strategies`.
- Estimación: 2 h.
