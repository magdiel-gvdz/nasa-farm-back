# Spec Delta

## Purpose

Permite evaluar la aptitud de cultivos y las estrategias de rotación bajo cambios hipotéticos de temperatura y lluvia, para explorar la sensibilidad de la zona al clima.

## ADDED Requirements

### Requirement: Parámetros de escenario
Los endpoints de aptitud y de rotaciones SHALL aceptar un cambio de temperatura `delta_t_c` entre −2 y +5 °C y un cambio de lluvia `delta_p_pct` entre −50 y +50 %, y SHALL rechazar valores fuera de rango con `422`.

#### Scenario: Escenario válido
- **WHEN** se pide la aptitud con `delta_t_c` igual a 2 y `delta_p_pct` igual a −20
- **THEN** la respuesta es `200` e incluye `scenario` con esos valores

#### Scenario: Valor fuera de rango
- **WHEN** se envía `delta_t_c` igual a 10
- **THEN** la respuesta es `422` con `error.code` igual a `validation_error`

### Requirement: Recálculo desde la serie diaria
Con un escenario distinto de cero, el sistema SHALL aplicar el cambio de temperatura a las temperaturas diarias y el de lluvia a la lluvia diaria, y SHALL recalcular heladas, días de calor, lluvia, evapotranspiración de referencia y balance hídrico antes de evaluar.

#### Scenario: Más calor
- **WHEN** se compara un escenario de +2 °C con el escenario cero para la misma celda
- **THEN** ninguna probabilidad de calor por decena disminuye y ninguna probabilidad de helada aumenta

#### Scenario: Menos lluvia
- **WHEN** se compara un escenario de −20 % de lluvia con el escenario cero
- **THEN** la necesidad de riego de cada estrategia de rotación es igual o mayor

### Requirement: Coherencia con los datos publicados
Con ambos cambios en cero, el resultado SHALL ser el mismo que sin parámetros de escenario. Los indicadores recalculados sin cambios MUST coincidir con los publicados por DATA con una diferencia máxima de 0.1 en cada probabilidad por decena.

#### Scenario: Escenario cero
- **WHEN** se pide la aptitud con ambos cambios en 0
- **THEN** el puntaje y las razones son idénticos a los de la petición sin escenario

### Requirement: Transparencia del escenario
Toda respuesta calculada con un escenario distinto de cero SHALL indicar los valores aplicados, el origen de la serie diaria, qué indicadores no se recalcularon y un texto que aclara que es un escenario hipotético y no un pronóstico.

#### Scenario: Indicadores no recalculados
- **WHEN** se obtiene una respuesta con escenario
- **THEN** `scenario.not_recomputed` incluye la humedad del suelo y el suelo descubierto

### Requirement: Respuesta interactiva
Una petición de aptitud o de rotaciones con escenario SHALL responder en menos de 2 segundos para una celda cuya serie diaria ya está disponible.

#### Scenario: Segundo movimiento del control
- **WHEN** se piden dos escenarios distintos seguidos para la misma geocerca
- **THEN** la segunda respuesta tarda menos de 2 segundos

### Requirement: Serie diaria no disponible
Si la serie diaria no puede obtenerse, las peticiones con escenario distinto de cero SHALL responder `503` con `error.code` igual a `daily_unavailable`, y las peticiones sin escenario MUST seguir funcionando.

#### Scenario: Sin serie diaria
- **WHEN** la serie diaria falla y se pide aptitud con `delta_t_c` igual a 2
- **THEN** la respuesta es `503` con `error.code` igual a `daily_unavailable` y la misma petición sin escenario responde `200`
