# Proposal

## Why

Un agricultor no lee tablas de probabilidades: pregunta "¿cuándo me conviene sembrar avena?". Un chat que consulta los datos de su zona y responde en lenguaje claro hace accesible todo lo demás. Es la primera extensión tras el MVP y la razón por la que el backend se ejecuta en un contenedor: las respuestas se transmiten por partes durante decenas de segundos.

## What Changes

- `POST /api/v1/chat/conversations` crea una conversación, opcionalmente ligada a una geocerca.
- `POST /api/v1/chat/conversations/{id}/messages` recibe un mensaje y responde como flujo de eventos (SSE): `status`, `tool`, `text`, `citation`, `card`, `done`, `error`.
- Cliente de Claude en Amazon Bedrock con respuesta en streaming.
- Latidos periódicos para que el balanceador no corte la conexión.
- Este cambio entrega el transporte y un modelo sin herramientas; las herramientas, el historial persistente, el prompt y los límites llegan en `e2` a `e5`.

## Capabilities

### New Capabilities
- `agronomist-chat`: conversación en streaming entre el agricultor y un asistente agrónomo basado en un modelo de lenguaje.

### Modified Capabilities

Ninguna.

## Impact

- Nuevos: `app/agent/` (`client.py`, `stream.py`, `events.py`), `app/api/routes/chat.py`, `tests/agent/`.
- Dependencia de ejecución nueva: SDK de Anthropic con soporte de Bedrock.
- Variables: `BEDROCK_MODEL_ID`, `CHAT_ENABLED`, región de Bedrock.
- Requiere acceso al modelo concedido en la cuenta (P2 del plan). Sin acceso, el MVP no se ve afectado.
- Tarea del plan: **E1** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 1 (Plataforma).
- Depende de: `a5-migrate-dev`, `b2-api-conventions`; acceso al modelo en Bedrock (P2 del plan).
- Estimación: 2.5 h.
