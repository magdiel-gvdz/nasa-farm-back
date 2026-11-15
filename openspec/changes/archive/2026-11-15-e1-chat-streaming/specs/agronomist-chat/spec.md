# Spec Delta

## Purpose

Permite al agricultor conversar con un asistente agrónomo basado en un modelo de lenguaje y recibir la respuesta en streaming, con visibilidad de lo que el asistente está haciendo.

## ADDED Requirements

### Requirement: Creación de conversación
`POST /api/v1/chat/conversations` SHALL crear una conversación del cliente, opcionalmente ligada a una geocerca suya, y responder `201` con `conversation_id`.

#### Scenario: Conversación ligada a una geocerca
- **WHEN** un cliente crea una conversación con el `field_id` de una geocerca suya
- **THEN** la respuesta es `201` con un `conversation_id` que empieza por `conv_`

#### Scenario: Geocerca ajena
- **WHEN** el `field_id` no pertenece al cliente
- **THEN** la respuesta es `404` con `error.code` igual a `not_found`

### Requirement: Respuesta como flujo de eventos
`POST /api/v1/chat/conversations/{id}/messages` SHALL responder con `Content-Type: text/event-stream` y emitir eventos con nombre y datos JSON de los tipos `status`, `tool`, `text`, `citation`, `card`, `done` y `error`.

#### Scenario: Respuesta de texto
- **WHEN** un cliente envía un mensaje a una conversación suya
- **THEN** el flujo empieza con un evento `status`, contiene uno o más eventos `text` con un campo `delta` y termina con un evento `done` que incluye `message_id` y el uso de tokens

#### Scenario: Conversación inexistente
- **WHEN** se envía un mensaje a una conversación que no existe o es de otro cliente
- **THEN** la respuesta es `404` en JSON con el sobre de error común y no se abre ningún flujo

### Requirement: Un único evento final
Todo flujo SHALL terminar con exactamente un evento `done` o un evento `error`, tras el cual el servidor cierra la conexión.

#### Scenario: Fallo del modelo a mitad de respuesta
- **WHEN** el modelo deja de responder después de emitir texto
- **THEN** el flujo emite un evento `error` con `code` igual a `llm_unavailable` y se cierra sin evento `done`

#### Scenario: Negativa del modelo
- **WHEN** el modelo se niega a responder
- **THEN** el flujo emite un evento `error` con `code` igual a `refused` y un mensaje apto para mostrar al usuario

### Requirement: Conexión mantenida
Mientras un flujo esté abierto, el servidor SHALL enviar datos o un latido al menos cada 15 segundos.

#### Scenario: Respuesta lenta
- **WHEN** el modelo tarda 40 segundos en producir el primer fragmento de texto
- **THEN** el cliente recibe latidos durante la espera y la conexión no se corta

### Requirement: Entrega sin almacenamiento intermedio
Los fragmentos de texto SHALL llegar al cliente a medida que se generan, no todos juntos al final.

#### Scenario: Entrega incremental
- **WHEN** se consume el flujo de una respuesta larga en el entorno desplegado
- **THEN** el primer evento `text` llega antes de que se emita el evento `done`, con una separación observable

### Requirement: Chat desactivable
Con el chat desactivado por configuración, los endpoints de chat SHALL responder `503` con `error.code` igual a `chat_disabled` sin invocar ningún modelo, y el resto de la API MUST seguir funcionando.

#### Scenario: Despliegue sin acceso al modelo
- **WHEN** `CHAT_ENABLED` es falso y se crea una conversación
- **THEN** la respuesta es `503` con `error.code` igual a `chat_disabled` y `GET /api/v1/crops` responde `200`

### Requirement: Cancelación al desconectar
Si el cliente cierra la conexión, el servidor SHALL dejar de generar la respuesta.

#### Scenario: Pestaña cerrada
- **WHEN** el cliente cierra la conexión a mitad de un flujo
- **THEN** la llamada al modelo se cancela y no se registran más fragmentos para ese mensaje
