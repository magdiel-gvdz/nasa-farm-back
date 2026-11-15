# Spec Delta

## Purpose

Define la superficie HTTP pública de la API de Field Shift: rutas, esquemas de petición y respuesta y reglas de versionado que consumen el frontend y el chat agrónomo.

## ADDED Requirements

### Requirement: Rutas versionadas
La API SHALL exponer todos sus endpoints de negocio bajo el prefijo `/api/v1` y SHALL mantener `GET /health` y `GET /ready` en la raíz para las comprobaciones de la plataforma.

#### Scenario: Ruta antigua
- **WHEN** un cliente llama a `GET /v1/sources`
- **THEN** la API responde `404`

#### Scenario: Ruta vigente
- **WHEN** un cliente llama a `GET /api/v1/sources`
- **THEN** la API responde `200` con una lista de fuentes

### Requirement: Endpoints del MVP
La API SHALL exponer: `GET /crops`, `GET /sources`, `POST /fields`, `GET /fields`, `GET /fields/{id}`, `PATCH /fields/{id}`, `DELETE /fields/{id}`, `GET /fields/{id}/profile`, `GET /fields/{id}/suitability` y `POST /fields/{id}/rotations`, todos bajo `/api/v1`.

#### Scenario: Documento del contrato
- **WHEN** se consulta `GET /openapi.json`
- **THEN** el documento describe cada uno de esos endpoints con esquema de respuesta y, cuando aplica, de petición

### Requirement: Claves en snake_case
Todas las claves de los cuerpos JSON de petición y respuesta MUST estar en `snake_case`.

#### Scenario: Respuesta de perfil
- **WHEN** se obtiene el perfil de una geocerca
- **THEN** ninguna clave del cuerpo contiene mayúsculas ni guiones

### Requirement: Respuestas fijas de referencia
Mientras un endpoint no tenga implementación real, la API SHALL devolver una respuesta fija que cumple su esquema y SHALL marcarla con el encabezado `X-Fieldshift-Mock: 1`. Una respuesta calculada con datos reales MUST NOT llevar ese encabezado.

#### Scenario: Endpoint aún no implementado
- **WHEN** se llama a `POST /api/v1/fields/{id}/rotations` antes de que exista el motor
- **THEN** la respuesta es `200`, cumple el esquema de rotaciones, contiene al menos tres estrategias y lleva `X-Fieldshift-Mock: 1`

### Requirement: Calendario de riesgos por decenas
El perfil SHALL expresar el calendario de riesgos en 36 decenas numeradas de 1 a 36 (días 1-10, 11-20 y 21 a fin de cada mes), no en semanas.

#### Scenario: Tamaño del calendario
- **WHEN** se obtiene un perfil
- **THEN** `climate.risk_calendar` tiene exactamente 36 elementos con `decade` de 1 a 36 sin repetir

### Requirement: Secciones sin dato explícitas
Cuando el sistema no dispone de datos para una sección del perfil, la API SHALL devolver esa sección como `null` y SHALL incluir una entrada en `gaps` que la nombre.

#### Scenario: Agua subterránea
- **WHEN** se obtiene un perfil y no existe fuente de agua subterránea
- **THEN** `water.groundwater` es `null` y `gaps` contiene una entrada cuyo `code` identifica esa ausencia

### Requirement: Contrato versionado en el repositorio
El repositorio SHALL contener el documento OpenAPI vigente y las comprobaciones automáticas MUST fallar cuando difiera del que genera la aplicación.

#### Scenario: Cambio de esquema sin regenerar
- **WHEN** un PR cambia un modelo de respuesta sin actualizar `contracts/openapi.json`
- **THEN** las comprobaciones fallan
