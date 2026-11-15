# Tasks

## 1. Cliente del modelo

- [x] 1.1 Consultar la documentación vigente de Amazon Bedrock y anotar en el PR: cliente (API Converse con `boto3`), identificador exacto del modelo, límite de tokens y cómo se informa una negativa; verificar con una llamada mínima desde la máquina local con el perfil del proyecto
  - Llamadas mínimas con `magidel-memo` en `us-east-1`: los modelos de Anthropic devuelven 403 o 404 (sin acceso); `qwen.qwen3-next-80b-a3b` responde en streaming con herramientas (`contentBlockStart.toolUse`, `contentBlockDelta.toolUse`, `messageStop.stopReason = tool_use`, `metadata.usage`). El modelo final, `mistral.mistral-large-3-675b-instruct`, se verificó igual en la evaluación local de 10 preguntas
- [x] 1.2 Añadir `BEDROCK_MODEL_ID`, región y `CHAT_ENABLED` a `app/config.py` (Converse no necesita dependencias nuevas); verificar que la imagen construye y que la configuración incompleta con el chat activo impide el arranque con un mensaje claro
- [x] 1.3 Implementar `app/agent/client.py` con una interfaz de generación en streaming y la implementación de Bedrock, más un cliente simulado guionizable para pruebas; verificar con una prueba que el simulado reproduce una secuencia de texto

## 2. Flujo de eventos

- [x] 2.1 Definir en `app/agent/events.py` los siete eventos y su serialización SSE; verificar con una prueba del formato exacto de `event:` y `data:` en una línea
- [x] 2.2 Implementar en `app/agent/stream.py` la traducción de la salida del cliente a eventos, con `status` inicial, un único evento final y el mapeo de fallos a `llm_unavailable`, `refused` e `internal_error`; verificar con pruebas de respuesta normal, fallo a mitad y negativa
- [x] 2.3 Implementar el latido cada 15 s (intervalo configurable) y la cancelación al desconectarse el cliente; verificar con pruebas de modelo lento con intervalo reducido y de desconexión

## 3. Endpoints

- [x] 3.1 Implementar `POST /chat/conversations` con validación de la geocerca del cliente y una conversación en memoria detrás de una interfaz de almacenamiento; verificar con pruebas de `201` y de geocerca ajena
- [x] 3.2 Implementar `POST /chat/conversations/{id}/messages` con respuesta en streaming, cabeceras `Cache-Control: no-cache` y `X-Accel-Buffering: no`, y errores previos al flujo en JSON; verificar con pruebas de flujo completo y de `404`
- [x] 3.3 Implementar el interruptor `chat_disabled`; verificar con una prueba de chat desactivado y catálogo accesible
- [x] 3.4 Añadir los endpoints y los eventos a `contracts/openapi.json` y a `docs/api-contract.md` con un ejemplo de consumo con `fetch`; verificar que la comprobación del contrato pasa

## 4. Verificación desplegada

- [ ] 4.1 En un preview con acceso al modelo, enviar un mensaje con `curl -N` y verificar que los eventos `text` llegan de forma incremental y que el flujo termina con `done`; anotar en el PR el tiempo hasta el primer fragmento
- [ ] 4.2 Verificar en el preview que una respuesta de más de 60 s (o una pausa forzada) no se corta gracias a los latidos
