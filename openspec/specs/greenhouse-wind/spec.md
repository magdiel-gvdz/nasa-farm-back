# greenhouse-wind Specification

## Purpose
Estima el riesgo de que el viento dañe la estructura de un invernadero, a partir del registro histórico de viento de su zona y de la resistencia declarada por el fabricante.

## Requirements

### Requirement: Evaluación de viento para invernaderos
`GET /api/v1/fields/{id}/greenhouse` SHALL devolver, para una geocerca de tipo invernadero, los niveles de retorno de viento a 10, 25 y 50 años, la resistencia declarada, la probabilidad anual de superarla, un estado y los meses de mayor riesgo.

#### Scenario: Invernadero con resistencia declarada
- **WHEN** se consulta un invernadero con `rated_wind_kmh` igual a 100
- **THEN** la respuesta es `200` con tres niveles de retorno crecientes, `annual_exceedance_probability` entre 0 y 1 y `status` igual a `ok`, `warn` o `bad`

#### Scenario: Geocerca que no es invernadero
- **WHEN** se consulta una geocerca de tipo `field`
- **THEN** la respuesta es `409` con `error.code` igual a `not_a_greenhouse`

#### Scenario: Resistencia no declarada
- **WHEN** el invernadero no tiene `rated_wind_kmh`
- **THEN** la respuesta incluye los niveles de retorno, `status` es `null` y `gaps` indica que falta la resistencia de la estructura

### Requirement: Niveles de retorno
El sistema SHALL estimar los niveles de retorno ajustando una distribución de Gumbel a los máximos anuales del viento máximo diario, usando solo años con al menos 360 días de datos.

#### Scenario: Recuperación de parámetros conocidos
- **WHEN** se ajusta una muestra simulada de una Gumbel con parámetros conocidos
- **THEN** los niveles de retorno estimados difieren menos de un 10 % de los teóricos

### Requirement: Viento sostenido y ráfaga estimada
La respuesta SHALL distinguir el viento sostenido del dato y la ráfaga estimada, SHALL declarar el factor de ráfaga aplicado y SHALL comparar la resistencia de la estructura con la ráfaga estimada.

#### Scenario: Factor declarado
- **WHEN** se obtiene la evaluación
- **THEN** cada nivel de retorno tiene `sustained_kmh` y `estimated_gust_kmh`, y `gust_factor_assumed` es 1.4 salvo configuración distinta

### Requirement: Fiabilidad según el registro
Con menos de 15 años completos de datos, el sistema SHALL marcar la evaluación con confianza baja y declarar el vacío; con menos de 5, MUST NOT devolver niveles de retorno.

#### Scenario: Solo diez años
- **WHEN** la serie diaria cubre 2016-2025
- **THEN** `confidence` es `low` y `gaps` contiene `short_wind_record` con el número de años usados

#### Scenario: Registro insuficiente
- **WHEN** hay menos de 5 años completos
- **THEN** `return_levels_kmh` es `null` y `gaps` lo explica

### Requirement: Límites declarados
La respuesta SHALL indicar que el viento procede de un modelo a escala de unos 55 km, que es el máximo de medias horarias y no la ráfaga instantánea, y que la topografía local puede aumentarlo; las secciones de luz, temperatura, CO₂ y granizo SHALL ser `null` con su vacío declarado.

#### Scenario: Nota de la fuente
- **WHEN** se obtiene la evaluación
- **THEN** `wind.note` menciona la escala del dato y la necesidad de validar con el fabricante o con registros locales
