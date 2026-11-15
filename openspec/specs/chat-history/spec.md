# chat-history Specification

## Purpose
Conserva las conversaciones del chat agrónomo para que el usuario pueda retomarlas y para que el asistente mantenga el contexto entre turnos.

## Requirements

### Requirement: Conversaciones persistentes
Las conversaciones y sus mensajes SHALL conservarse tras reiniciar o redesplegar el servicio y SHALL estar disponibles desde cualquier instancia.

#### Scenario: Redespliegue a mitad de conversación
- **WHEN** un usuario envía un mensaje, el servicio se redespliega y envía otro mensaje en la misma conversación
- **THEN** el asistente responde teniendo en cuenta el primer mensaje

### Requirement: Contexto completo para el modelo
El sistema SHALL guardar el contenido íntegro de cada turno del asistente, incluidos usos de herramientas, resultados y bloques de razonamiento, y SHALL reenviarlo al modelo sin modificar en los turnos siguientes.

#### Scenario: Pregunta de seguimiento
- **WHEN** el usuario pregunta "¿y en mayo?" después de una evaluación de maíz en abril
- **THEN** el asistente evalúa maíz en mayo sin pedir de nuevo el cultivo

### Requirement: Historial visible
`GET /api/v1/chat/conversations/{id}` SHALL devolver, en orden, los mensajes del usuario y del asistente con su texto, sus tarjetas y sus citas, y MUST NOT incluir bloques de razonamiento ni resultados de herramientas en bruto.

#### Scenario: Recarga de la página
- **WHEN** el frontend pide el historial de una conversación con dos intercambios
- **THEN** recibe cuatro mensajes en orden cronológico, con las tarjetas y citas de cada respuesta del asistente

### Requirement: Aislamiento por cliente
Una conversación MUST ser accesible únicamente con el `X-Client-Id` que la creó.

#### Scenario: Conversación ajena
- **WHEN** otro cliente pide el historial o envía un mensaje a la conversación
- **THEN** la respuesta es `404` con `error.code` igual a `not_found`

### Requirement: Respuestas interrumpidas
Si una respuesta del asistente termina en error o el cliente se desconecta, el sistema MUST NOT guardar un turno incompleto que impida continuar la conversación.

#### Scenario: Fallo del modelo
- **WHEN** una respuesta termina con el evento `error` y el usuario envía otro mensaje
- **THEN** el nuevo mensaje se procesa con normalidad y el historial visible marca la respuesta fallida como tal

### Requirement: Tope de turnos
Una conversación SHALL admitir como máximo 40 mensajes del usuario; al superarlo, el envío SHALL responder `409` con `error.code` igual a `conversation_full`.

#### Scenario: Conversación llena
- **WHEN** se envía el mensaje 41 del usuario
- **THEN** la respuesta es `409` con `error.code` igual a `conversation_full` y un mensaje que invita a abrir una conversación nueva
