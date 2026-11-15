# Spec Delta

## Purpose

Entrega el perfil agroclimático histórico de la zona donde está una geocerca, con la procedencia de cada cifra y una declaración explícita de lo que los datos no permiten afirmar.

## ADDED Requirements

### Requirement: Perfil de una geocerca
`GET /api/v1/fields/{id}/profile` SHALL responder `200` con el perfil de la celda asignada a la geocerca, incluyendo `status` igual a `ready`, `field_id`, `cell_id`, `zone_id`, `data_version` y `computed_at`.

#### Scenario: Geocerca existente
- **WHEN** un cliente pide el perfil de una geocerca suya
- **THEN** la respuesta es `200`, cumple el esquema del contrato y `cell_id` coincide con el de la geocerca

#### Scenario: Geocerca ajena o inexistente
- **WHEN** se pide el perfil de una geocerca que no pertenece al cliente
- **THEN** la respuesta es `404`

### Requirement: Calendario de riesgos
El perfil SHALL incluir, para cada una de las 36 decenas, la probabilidad de helada, de helada fuerte, de calor por cada umbral disponible, de lluvia intensa, de estrés hídrico y de suelo descubierto, la lluvia mediana, y si la decena es vulnerable con sus motivos. Cada probabilidad SHALL acompañarse del umbral que la define.

#### Scenario: Decena vulnerable
- **WHEN** DATA marca una decena como vulnerable por helada
- **THEN** su entrada tiene `vulnerable` verdadero y `vulnerable_reasons` contiene `frost`

#### Scenario: Umbral declarado
- **WHEN** se obtiene el perfil
- **THEN** `climate.frost.threshold_c` y la lista de umbrales de calor reflejan los valores con los que DATA calculó los indicadores

### Requirement: Resumen mensual
El perfil SHALL resumir por mes las heladas, la lluvia, el calor y el viento. La probabilidad mensual de un evento SHALL calcularse como la fracción de años con al menos un evento en cualquiera de las decenas del mes, y MUST NOT obtenerse sumando o promediando probabilidades por decena.

#### Scenario: Probabilidad mensual de helada
- **WHEN** en 4 de 10 años hubo al menos una helada en alguna decena de marzo
- **THEN** `climate.frost.by_month` para el mes 3 tiene `prob_any_frost` igual a 0.4

### Requirement: Suelo, agua y vegetación
El perfil SHALL incluir el suelo por profundidad con valor medio y rango P05-P95, clase textural y materia orgánica estimada; la humedad del suelo en percentiles con la fuente efectivamente usada; el balance de lluvia menos evapotranspiración de referencia; y el NDVI con los meses de suelo descubierto. Una sección sin datos SHALL ser `null`.

#### Scenario: NDVI aún no publicado
- **WHEN** la versión de datos no incluye NDVI
- **THEN** `vegetation` es `null` y `gaps` contiene `ndvi_not_available`

### Requirement: Procedencia
Cada sección del perfil con datos SHALL llevar un `source_id`, y `sources` SHALL contener exactamente las fuentes referenciadas, con resolución, periodo y clase de dato.

#### Scenario: Referencias resueltas
- **WHEN** se obtiene un perfil
- **THEN** todo `source_id` presente en el cuerpo aparece una vez en `sources`

### Requirement: Vacíos de información
El perfil SHALL declarar en `gaps`: siempre la resolución zonal de 9 km y la ausencia de análisis de laboratorio; el clima compartido cuando varias celdas usan la misma serie; la diferencia de elevación cuando supera 300 m; el uso de humedad de modelo cuando no hay SMAP; y cada sección sin datos. Cada entrada SHALL tener `code`, `severity` y `message`.

#### Scenario: Celda de sierra
- **WHEN** la elevación de la celda difiere 450 m de la del cuadro climático
- **THEN** `gaps` contiene `elevation_mismatch` con severidad `medium` y el mensaje indica que las temperaturas son una estimación corregida por altura

#### Scenario: Vacío permanente
- **WHEN** se obtiene cualquier perfil
- **THEN** `gaps` contiene `zonal_resolution_9km`

### Requirement: Lenguaje zonal
Los textos del perfil MUST referirse a la zona o celda de 9 km y MUST NOT afirmar valores de la parcela.

#### Scenario: Mensajes del perfil
- **WHEN** se revisan todos los campos `message` y `note` de un perfil en español
- **THEN** ninguno contiene "tu parcela tiene" ni equivalente, y el de resolución menciona "celda de 9 km"
