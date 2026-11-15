# api-conventions Specification

## Purpose
Define las reglas comunes a todos los endpoints de la API: formato de errores, identificación del cliente sin inicio de sesión, idioma de los textos, CORS y señal de disponibilidad.

## Requirements

### Requirement: Sobre de error único
Toda respuesta de error de la API SHALL tener el cuerpo `{"error": {"code": string, "message": string, "details": object}}`, con un `code` estable en `snake_case` y un estado HTTP acorde.

#### Scenario: Cuerpo inválido
- **WHEN** un cliente envía a `POST /api/v1/fields` un cuerpo que no cumple el esquema
- **THEN** la respuesta es `422` con `error.code` igual a `validation_error` y `error.details` indica los campos inválidos

#### Scenario: Recurso inexistente
- **WHEN** un cliente pide una geocerca que no existe
- **THEN** la respuesta es `404` con `error.code` igual a `not_found`

#### Scenario: Error inesperado
- **WHEN** ocurre una excepción no controlada
- **THEN** la respuesta es `500` con `error.code` igual a `internal_error` y el cuerpo no contiene trazas ni nombres de recursos internos

### Requirement: Identidad del cliente
Los endpoints que leen o escriben datos del usuario SHALL exigir el encabezado `X-Client-Id` con un UUID válido y SHALL usarlo como único separador de datos entre usuarios.

#### Scenario: Encabezado ausente
- **WHEN** se llama a `GET /api/v1/fields` sin `X-Client-Id`
- **THEN** la respuesta es `400` con `error.code` igual a `missing_client_id`

#### Scenario: Encabezado con formato inválido
- **WHEN** `X-Client-Id` no es un UUID
- **THEN** la respuesta es `400` con `error.code` igual a `invalid_client_id`

#### Scenario: Catálogos sin identidad
- **WHEN** se llama a `GET /api/v1/crops` sin `X-Client-Id`
- **THEN** la respuesta es `200`

### Requirement: Idioma de los textos
La API SHALL devolver los textos explicativos en el idioma indicado por `Accept-Language` cuando sea `es` o `en`, y en español en cualquier otro caso.

#### Scenario: Inglés solicitado
- **WHEN** una petición lleva `Accept-Language: en`
- **THEN** los campos `message` de `gaps` y de errores están en inglés

#### Scenario: Idioma no admitido
- **WHEN** una petición lleva `Accept-Language: fr`
- **THEN** los textos se devuelven en español

### Requirement: CORS para el frontend
La API SHALL aceptar desde los orígenes configurados los métodos `GET`, `POST`, `PATCH`, `DELETE` y `OPTIONS` con los encabezados `Content-Type`, `X-Client-Id` y `Accept-Language`, y SHALL exponer `X-Fieldshift-Mock`. Un origen no configurado MUST NOT recibir encabezados de permiso.

#### Scenario: Preflight de borrado
- **WHEN** un origen configurado envía `OPTIONS` para `DELETE` con `X-Client-Id`
- **THEN** la respuesta permite el método y el encabezado

#### Scenario: Origen desconocido
- **WHEN** un origen no configurado envía una petición
- **THEN** la respuesta no incluye `access-control-allow-origin`

### Requirement: Señal de disponibilidad
`GET /ready` SHALL responder `200` con la versión de datos cargada cuando el proveedor de datos está listo, y `503` con `error.code` igual a `data_unavailable` cuando no lo está. `GET /health` MUST responder `200` sin depender de datos ni de AWS.

#### Scenario: Datos aún no cargados
- **WHEN** el proveedor de datos no ha terminado su primera carga
- **THEN** `GET /ready` responde `503` y `GET /health` responde `200`
