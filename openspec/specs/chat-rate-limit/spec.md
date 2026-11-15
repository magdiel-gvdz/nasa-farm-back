# chat-rate-limit Specification

## Purpose
Protege el presupuesto del proyecto y la disponibilidad del chat agrónomo limitando cuánto puede usarlo cada cliente y el conjunto de todos ellos.

## Requirements

### Requirement: Límite por cliente
El sistema SHALL limitar los mensajes de chat de cada `X-Client-Id` por minuto y por día, con valores configurables, y SHALL rechazar los excedentes con `429`, `error.code` igual a `rate_limited` y la cabecera `Retry-After`.

#### Scenario: Ráfaga
- **WHEN** un cliente envía más mensajes en un minuto que el límite configurado
- **THEN** el mensaje excedente recibe `429` con `Retry-After` en segundos y no se invoca al modelo

#### Scenario: Límite diario
- **WHEN** un cliente supera su límite diario
- **THEN** recibe `429` con un mensaje que indica que podrá continuar al día siguiente

#### Scenario: Otro cliente
- **WHEN** un cliente está limitado y otro distinto envía un mensaje
- **THEN** el segundo recibe respuesta normal

### Requirement: Presupuesto diario global
El sistema SHALL contar los mensajes de chat de todos los clientes por día y, al alcanzar el presupuesto configurado, SHALL rechazar los nuevos con `503` y `error.code` igual a `chat_budget_exhausted` hasta el día siguiente (UTC).

#### Scenario: Presupuesto agotado
- **WHEN** el total diario alcanza el presupuesto
- **THEN** los nuevos mensajes reciben `503` con `error.code` igual a `chat_budget_exhausted` y el resto de la API sigue respondiendo

#### Scenario: Varias instancias
- **WHEN** el servicio tiene dos instancias
- **THEN** el presupuesto diario se cuenta de forma conjunta

### Requirement: Tamaño acotado
El sistema SHALL rechazar con `422` los mensajes de usuario de más de 2,000 caracteres y SHALL limitar los tokens de salida de cada respuesta a un máximo configurable.

#### Scenario: Mensaje demasiado largo
- **WHEN** el usuario envía un mensaje de 5,000 caracteres
- **THEN** la respuesta es `422` con `error.code` igual a `message_too_long`

### Requirement: Catálogos no limitados
Los límites del chat MUST NOT afectar a los endpoints que no invocan al modelo.

#### Scenario: Cliente limitado consulta su perfil
- **WHEN** un cliente con el chat limitado pide el perfil de su geocerca
- **THEN** la respuesta es `200`
