# Proposal

## Why

La API es pública y sin inicio de sesión, y cada mensaje del chat cuesta dinero en Bedrock. Antes había un límite de peticiones en API Gateway; con el balanceador de ECS ya no hay ninguno. Un cliente descuidado o malicioso, o la URL publicada durante la demo, podría agotar el presupuesto del proyecto (100 USD al mes) en poco tiempo.

## What Changes

- Límite de mensajes de chat por cliente, por minuto y por día.
- Tope de tamaño del mensaje del usuario y de tokens de cada respuesta.
- Presupuesto diario global de mensajes, tras el cual el chat se desactiva solo hasta el día siguiente.
- Respuestas `429` con el tiempo de espera.

## Capabilities

### New Capabilities
- `chat-rate-limit`: límites de uso y de gasto del chat agrónomo.

### Modified Capabilities

Ninguna.

## Impact

- Nuevos: `app/agent/limits.py`, cambios en `app/api/routes/chat.py`.
- Contadores diarios en la tabla del entorno; contadores por minuto en memoria.
- Variables: `CHAT_MAX_PER_MINUTE`, `CHAT_MAX_PER_DAY`, `CHAT_DAILY_BUDGET`, `CHAT_MAX_OUTPUT_TOKENS`.
- Tarea del plan: **E5** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 1 (Plataforma).
- Depende de: `e1-chat-streaming`.
- Estimación: 1 h.
