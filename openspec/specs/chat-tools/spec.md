# chat-tools Specification

## Purpose
Define las herramientas con las que el asistente agrónomo consulta los datos y motores de Field Shift durante una conversación, de modo que toda cifra de sus respuestas proceda del sistema y no del modelo.

## Requirements

### Requirement: Herramientas disponibles
El asistente SHALL disponer de herramientas para: listar las geocercas del cliente, leer secciones del perfil de una geocerca, leer un tramo del calendario de riesgos, evaluar un cultivo en un mes, obtener la matriz de aptitud, comparar rotaciones y listar el catálogo de cultivos. Cada herramienta SHALL devolver el mismo contenido que el endpoint equivalente.

#### Scenario: Pregunta sobre fechas de siembra
- **WHEN** el usuario pregunta cuándo sembrar avena en su geocerca activa
- **THEN** el asistente invoca la evaluación de aptitud o el calendario de riesgos antes de responder

#### Scenario: Coherencia con la API
- **WHEN** el asistente evalúa maíz en abril para una geocerca
- **THEN** el resultado que recibe es idéntico al de `GET /api/v1/fields/{id}/suitability` con los mismos parámetros

### Requirement: Aislamiento por cliente
Las herramientas MUST operar únicamente sobre geocercas del cliente de la conversación, con independencia de los identificadores que proponga el modelo.

#### Scenario: Identificador de otro cliente
- **WHEN** el modelo invoca una herramienta con el `field_id` de una geocerca de otro cliente
- **THEN** la herramienta devuelve un error de geocerca no encontrada y no revela ningún dato

### Requirement: Visibilidad del uso de herramientas
Cada invocación SHALL emitir un evento `tool` con estado `running` y una etiqueta legible en el idioma del usuario, y otro con estado `done` o `failed` al terminar.

#### Scenario: Consulta del calendario
- **WHEN** el asistente consulta el calendario de riesgos
- **THEN** el flujo contiene un evento `tool` con `state` igual a `running` y después otro con `state` igual a `done` para la misma herramienta

### Requirement: Tarjetas de resultado
Cuando una herramienta devuelve una evaluación de aptitud o una comparación de rotaciones, el flujo SHALL emitir un evento `card` con el tipo y el objeto completo.

#### Scenario: Comparación de rotaciones en el chat
- **WHEN** el asistente compara rotaciones
- **THEN** el flujo contiene un evento `card` con `type` igual a `rotations` y un `payload` que cumple el esquema de rotaciones

### Requirement: Citas de fuentes
Por cada fuente presente en los resultados de las herramientas usadas en una respuesta, el flujo SHALL emitir un evento `citation` con `source_id` y una etiqueta con nombre y periodo, sin repetir fuentes.

#### Scenario: Respuesta basada en clima
- **WHEN** el asistente responde usando el calendario de riesgos
- **THEN** el flujo contiene un evento `citation` con el `source_id` de la fuente climática

### Requirement: Fallos de herramienta tolerados
Si una herramienta falla o recibe argumentos inválidos, el asistente SHALL recibir el error como resultado y la conversación MUST continuar. El número de invocaciones por mensaje SHALL estar limitado.

#### Scenario: Cultivo inexistente
- **WHEN** el modelo pide evaluar un cultivo que no está en el catálogo
- **THEN** la herramienta devuelve `crop_not_found`, el flujo emite `tool` con `state` igual a `failed` y el asistente responde sin que el flujo termine en `error`

#### Scenario: Bucle de herramientas
- **WHEN** el modelo intenta más de 8 invocaciones en un mismo mensaje
- **THEN** el sistema deja de ofrecer herramientas y el asistente responde con lo obtenido
