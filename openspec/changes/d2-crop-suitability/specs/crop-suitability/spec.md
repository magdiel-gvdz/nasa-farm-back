# Spec Delta

## Purpose

Evalúa, de forma determinista y explicada, si un cultivo puede sembrarse en un mes dado en la zona de una geocerca, a partir del clima histórico, el suelo y el agua disponible.

## ADDED Requirements

### Requirement: Evaluación de un cultivo y mes
`GET /api/v1/fields/{id}/suitability` con `crop_id` y `planting_month` SHALL devolver el estado, un puntaje de 0 a 100, la ventana de cosecha estimada, una razón por cada factor (`frost`, `heat`, `water`, `soil`) y la confianza.

#### Scenario: Evaluación correcta
- **WHEN** se evalúa maíz sembrado en abril en una geocerca del Sureste
- **THEN** la respuesta es `200` con `score` entre 0 y 100, cuatro razones y cada razón tiene `status`, `detail` y `source_id`

#### Scenario: Cultivo desconocido
- **WHEN** `crop_id` no existe en el catálogo
- **THEN** la respuesta es `404` con `error.code` igual a `crop_not_found`

#### Scenario: Mes inválido
- **WHEN** `planting_month` es 13
- **THEN** la respuesta es `422`

### Requirement: Estado según el puntaje
El estado SHALL ser `suitable` con puntaje de 70 o más, `marginal` de 40 a 69 e `unsuitable` por debajo de 40, con cortes tomados de configuración. Un factor en estado `bad` que sea excluyente SHALL limitar el puntaje a menos de 40.

#### Scenario: Helada excluyente
- **WHEN** un cultivo no tolerante a helada tiene su ciclo sobre decenas con probabilidad de helada alta
- **THEN** el factor `frost` es `bad` y el estado es `unsuitable`

### Requirement: Factor helada
El motor SHALL evaluar la probabilidad de helada en las decenas que ocupa el ciclo del cultivo y SHALL considerarla aceptable si el cultivo tolera heladas.

#### Scenario: Cultivo tolerante
- **WHEN** se evalúa avena sembrada en noviembre en una zona con heladas invernales
- **THEN** el factor `frost` no es `bad` y su detalle menciona la tolerancia del cultivo

### Requirement: Factor calor
El motor SHALL evaluar los días de calor durante la floración usando el umbral disponible más cercano a la temperatura crítica del cultivo, y SHALL indicar en el detalle qué umbral usó.

#### Scenario: Umbral aproximado
- **WHEN** la temperatura crítica del cultivo es 34 °C y los umbrales disponibles son 30, 32, 35 y 38
- **THEN** el detalle del factor `heat` indica que se usó el umbral de 35 °C

### Requirement: Factor agua
El motor SHALL comparar la demanda del ciclo, calculada con la evapotranspiración de referencia y los coeficientes Kc del cultivo, con la lluvia efectiva más el riego disponible de la geocerca, y SHALL informar el déficit en milímetros.

#### Scenario: Déficit con riego insuficiente
- **WHEN** la demanda es 620 mm, la lluvia efectiva 240 mm y el riego disponible 200 mm
- **THEN** el factor `water` es `bad` o `warn` y su detalle indica un déficit de 180 mm

#### Scenario: Geocerca sin dato de riego
- **WHEN** la geocerca no declara riego
- **THEN** el motor evalúa en temporal (riego 0) y lo indica en el detalle

### Requirement: Factor suelo
El motor SHALL comparar el pH de la capa superficial y la clase textural con los rangos del cultivo.

#### Scenario: pH fuera de rango
- **WHEN** el pH de la zona es 8.4 y el cultivo admite de 5.5 a 7.5
- **THEN** el factor `soil` es `warn` o `bad` y el detalle incluye ambos valores

### Requirement: Matriz de aptitud
Sin `crop_id`, el endpoint SHALL devolver para cada cultivo del catálogo los puntajes y estados de los 12 meses de siembra.

#### Scenario: Matriz completa
- **WHEN** se pide la matriz
- **THEN** cada cultivo tiene 12 puntajes y 12 estados, coherentes con la evaluación individual del mismo cultivo y mes

### Requirement: Datos faltantes sin fallo
Si falta el dato de un factor, el motor SHALL marcar ese factor como `unknown`, reducir la confianza y calcular el puntaje con los demás; MUST NOT fallar la petición.

#### Scenario: Sin suelo publicado
- **WHEN** la celda no tiene perfil de suelo
- **THEN** la respuesta es `200`, el factor `soil` es `unknown` y `confidence` es `low`

### Requirement: Resultado reproducible y trazable
La misma entrada con la misma versión de datos SHALL producir la misma salida, y cada razón SHALL citar una fuente presente en el catálogo de fuentes.

#### Scenario: Dos llamadas iguales
- **WHEN** se evalúa dos veces el mismo cultivo, mes y geocerca
- **THEN** las dos respuestas son idénticas
