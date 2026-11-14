# Proposal

## Why

Con herramientas, el asistente puede responder con datos; falta asegurar que lo haga como debe un asesor agrícola responsable: sin cifras propias, hablando de la zona y no de la parcela, citando fuente y periodo, y diciendo qué tiene que validar un agrónomo local. El reto evalúa expresamente la incertidumbre y el papel del experto local, y un asistente que promete de más pone en riesgo una siembra.

## What Changes

- Instrucciones de sistema del asistente con sus reglas de comportamiento.
- Contexto variable por mensaje: geocerca activa, zona, fecha e idioma.
- Conjunto de 10 preguntas reales de un agrónomo con su lista de comprobación, versionado en el repositorio, y un script para ejecutarlas.

## Capabilities

### New Capabilities
- `chat-guidelines`: reglas de comportamiento del asistente agrónomo ante el usuario.

### Modified Capabilities

Ninguna.

## Impact

- Nuevos: `app/agent/prompts/system.md`, `app/agent/context.py`, `evals/chat/questions.yaml`, `scripts/run_chat_eval.py`, `docs/chat-eval.md`.
- Sin cambios en endpoints.
- Tarea del plan: **E4** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 4 (Motores).
- Depende de: `e2-chat-tools`.
- Estimación: 1.5 h.
