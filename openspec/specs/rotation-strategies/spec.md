# rotation-strategies Specification

## Purpose
Genera, simula, puntúa y explica estrategias de rotación de cultivos para una geocerca, de modo que el agricultor pueda comparar su rotación actual con alternativas y entender en qué se basa cada una.

## Requirements

### Requirement: Comparación de al menos tres estrategias
`POST /api/v1/fields/{id}/rotations` SHALL devolver al menos tres estrategias, una de las cuales es la rotación actual de la geocerca marcada con `is_current` verdadero, y como máximo `max_strategies`.

#### Scenario: Comparación básica
- **WHEN** se piden rotaciones para una geocerca con rotación actual declarada
- **THEN** la respuesta contiene tres o más estrategias, exactamente una con `is_current` verdadero

#### Scenario: Sin rotación actual
- **WHEN** la geocerca no tiene rotación actual declarada
- **THEN** la respuesta es `422` con `error.code` igual a `current_rotation_required`

#### Scenario: Pocas alternativas aptas
- **WHEN** las restricciones dejan menos de dos alternativas plenamente aptas
- **THEN** la respuesta sigue teniendo tres estrategias y las admitidas con condiciones lo declaran en `risks_local_review`

### Requirement: Contenido de cada estrategia
Cada estrategia SHALL incluir la secuencia por año y temporada con fechas de siembra y cosecha, las métricas, los puntajes por prioridad, el puntaje global y la confianza, además de listas no vacías de `why`, `evidence`, `benefits`, `gaps` y `risks_local_review`.

#### Scenario: Explicación completa
- **WHEN** se obtiene cualquier estrategia, incluida la actual
- **THEN** sus cinco listas explicativas tienen al menos un elemento cada una

### Requirement: Evidencia trazable
Cada elemento de `evidence` SHALL contener una afirmación con un valor calculado y un `source_id` presente en el catálogo de fuentes.

#### Scenario: Evidencia de suelo descubierto
- **WHEN** una estrategia deja el suelo sin cultivo en invierno
- **THEN** su evidencia incluye los días de suelo descubierto al año con el `source_id` de la fuente de vegetación o, si no hay NDVI, de la secuencia declarada

### Requirement: Métricas de la simulación
Cada estrategia SHALL informar, como media anual sobre el horizonte simulado: demanda de agua y necesidad de riego en mm, balance aproximado de nitrógeno en kg/ha, tendencia de materia orgánica, días de suelo descubierto, índice de exposición a erosión de 0 a 1 y puntaje de ruptura de plagas.

#### Scenario: Efecto de una leguminosa
- **WHEN** una alternativa sustituye un ciclo del cultivo principal por una leguminosa
- **THEN** su balance de nitrógeno es mayor que el de la rotación actual

#### Scenario: Efecto de un cultivo de cobertura
- **WHEN** una alternativa ocupa el barbecho de invierno con un cultivo de cobertura
- **THEN** sus días de suelo descubierto y su índice de exposición a erosión son menores que los de la rotación actual

#### Scenario: Misma familia en años seguidos
- **WHEN** una estrategia repite la misma familia botánica en todas las temporadas
- **THEN** su puntaje de ruptura de plagas es el mínimo

### Requirement: Prioridades del agricultor
El puntaje global SHALL ser la combinación de los puntajes por prioridad ponderada por los pesos de 0 a 5 que envía el agricultor, y `recommended_id` SHALL ser la estrategia con mayor puntaje global, que puede ser la actual.

#### Scenario: Prioridad de ahorro de agua
- **WHEN** se envía `save_water` con peso 5 y el resto con peso 0
- **THEN** la estrategia recomendada es la de menor necesidad de riego

#### Scenario: Todos los pesos en cero
- **WHEN** todas las prioridades valen 0
- **THEN** la respuesta es `200` y el puntaje global usa pesos iguales

### Requirement: Restricciones del agricultor
Ninguna alternativa SHALL incluir cultivos excluidos por el agricultor ni cultivos que requieran equipo no disponible; una alternativa cuya necesidad de riego supere el límite declarado SHALL indicarlo como riesgo.

#### Scenario: Cultivo excluido
- **WHEN** se envía `exclude_crops` con `algodon`
- **THEN** ninguna alternativa contiene `algodon`

#### Scenario: Riego insuficiente
- **WHEN** una alternativa necesita 500 mm de riego y el límite es 400 mm
- **THEN** sus `risks_local_review` incluyen el déficit de 100 mm

### Requirement: Límites declarados y apoyo a la decisión
Toda estrategia SHALL declarar en `gaps` la resolución zonal de los datos y la ausencia de análisis de laboratorio, y en `risks_local_review` al menos un aspecto que debe validar un agrónomo o productor local. La respuesta SHALL incluir un `disclaimer` que indica que la herramienta apoya y no sustituye el juicio local.

#### Scenario: Aviso presente
- **WHEN** se obtiene una respuesta de rotaciones en inglés
- **THEN** `disclaimer` está en inglés y cada estrategia tiene al menos un riesgo de revisión local

### Requirement: Resultado reproducible
La misma petición con la misma versión de datos y de catálogo SHALL producir la misma respuesta, sin intervención de modelos de lenguaje ni aleatoriedad.

#### Scenario: Dos llamadas iguales
- **WHEN** se envía dos veces la misma petición
- **THEN** las respuestas son idénticas
