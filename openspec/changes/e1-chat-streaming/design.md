# Design

## Context

La API corre en un contenedor de larga vida detrás del balanceador administrado de ECS Express Mode, que corta conexiones sin tráfico tras 60 segundos y cuyo ajuste no está expuesto. El rol de la API tiene permiso para invocar modelos en Bedrock. `docs/backend-handoff.md` §9 propone nombres concretos de cliente, modelo y parámetros que no se han verificado.

## Goals / Non-Goals

**Goals:**
- Que el frontend pueda pintar la respuesta según llega y saber qué está haciendo el asistente.
- Que un fallo del modelo nunca deje la conexión colgada.

**Non-Goals:**
- Herramientas, persistencia, prompt definitivo y límites de uso (cambios `e2` a `e5`).
- WebSockets o reanudación de un flujo interrumpido.

## Decisions

- **SSE sobre POST** con `text/event-stream`: cada evento lleva `event:` y `data:` con JSON de una línea. Es lo que define el contrato del handoff §6.11 y funciona con `fetch` en el navegador.
- **Latido cada 15 segundos** como línea de comentario SSE (`: ping`), muy por debajo del corte de 60 s del balanceador. Se envía también mientras el modelo piensa o una herramienta trabaja.
- **API Converse de Bedrock con modelo configurable** (decisión del 15 de noviembre de 2026). La cuenta no tiene acceso a los modelos de Anthropic en Bedrock; se usa un modelo disponible y se elige con `BEDROCK_MODEL_ID`, de modo que pasar a Claude cuando haya acceso solo cambia esa variable. Modelo inicial: `qwen.qwen3-next-80b-a3b`, elegido con una prueba de uso de herramientas en español frente a Amazon Nova Pro, Mistral Large 3, DeepSeek V3.2, Kimi K2.5, GLM-5 y gpt-oss-120b: fue el que respondió solo con los datos recibidos, sin añadir recomendaciones sin respaldo. Las negativas se detectan por los motivos de parada `content_filtered` y `guardrail_intervened`.
- **Capa propia de eventos.** `app/agent/stream.py` traduce los eventos de Converse a los siete eventos del contrato. Las rutas y las pruebas no dependen de Bedrock: en pruebas se inyecta un cliente simulado que emite una secuencia guionizada.
- **Orden garantizado:** `status` primero; `text` en fragmentos; exactamente un evento final, `done` o `error`. Tras el evento final se cierra la conexión.
- **Errores dentro del flujo.** Una vez enviada la cabecera `200`, cualquier fallo se comunica con el evento `error` (`llm_unavailable`, `refused`, `internal_error`). Antes de abrir el flujo, los errores usan el sobre JSON común (por ejemplo, conversación inexistente).
- **Interruptor `CHAT_ENABLED`.** Con valor falso, los endpoints de chat responden `503` con `chat_disabled` sin llamar al modelo. Permite desplegar sin acceso a Bedrock.
- **Conversación mínima en memoria** en este cambio, detrás de la interfaz que `e3-chat-history` implementará sobre DynamoDB.

## Risks / Trade-offs

- [El acceso al modelo no llega a tiempo] → `CHAT_ENABLED=false`; el resto del producto no depende del chat.
- [Algún intermediario almacena la respuesta completa antes de entregarla] → Cabeceras `Cache-Control: no-cache` y `X-Accel-Buffering: no`; se comprueba en un preview con `curl -N`.
- [El cliente cierra la pestaña a mitad de respuesta] → Se detecta la desconexión y se cancela la llamada al modelo para no gastar tokens.
