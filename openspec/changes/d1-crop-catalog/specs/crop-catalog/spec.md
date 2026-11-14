# Spec Delta

## Purpose

Mantiene el catálogo de cultivos con los requisitos agronómicos y aportes de cada uno, como fuente única para los motores de cálculo y para el frontend.

## ADDED Requirements

### Requirement: Consulta del catálogo
`GET /api/v1/crops` SHALL devolver todos los cultivos del catálogo con identificador estable, nombre en español e inglés, familia botánica, roles, ciclo en días, rangos de temperatura óptima y absoluta, tolerancia a helada, temperatura crítica de calor, necesidad de agua, rango de pH, coeficientes Kc y si fija nitrógeno.

#### Scenario: Lista de cultivos
- **WHEN** se consulta `GET /api/v1/crops`
- **THEN** la respuesta es `200` con al menos 5 cultivos y cada uno tiene `id`, `name.es`, `name.en`, `family`, `roles`, `cycle_days` y `kc`

#### Scenario: Roles necesarios para rotar
- **WHEN** se consulta el catálogo completo
- **THEN** existe al menos un cultivo con cada rol: `cash`, `legume`, `cover`, `forage` y `drought_tolerant`

### Requirement: Catálogo válido al arrancar
El sistema SHALL validar el catálogo completo al arrancar y MUST NOT arrancar con un catálogo inválido. Son inválidos: identificadores repetidos, rangos con mínimo mayor que máximo, Kc fuera de 0 a 1.5, roles o familias desconocidos y campos obligatorios ausentes.

#### Scenario: Rango invertido
- **WHEN** un cultivo declara `ph` con mínimo 7.5 y máximo 5.5
- **THEN** la aplicación no arranca y el error nombra el cultivo y el campo

#### Scenario: Identificador repetido
- **WHEN** dos cultivos comparten `id`
- **THEN** la aplicación no arranca y el error nombra el identificador

### Requirement: Datos para el motor de rotaciones
Cada cultivo SHALL declarar su balance de nitrógeno aproximado en kg/ha por ciclo, su aporte de residuo (`low`, `medium` o `high`), su profundidad de raíz y el equipo que requiere. El índice relativo de margen SHALL ser opcional.

#### Scenario: Leguminosa
- **WHEN** se consulta un cultivo con rol `legume`
- **THEN** `n_fixing` es verdadero y su balance de nitrógeno es positivo

### Requirement: Procedencia y revisión
Cada cultivo SHALL indicar la fuente de sus valores y si el rol científico los ha revisado.

#### Scenario: Cultivo de ejemplo sin revisar
- **WHEN** un cultivo procede de los valores iniciales no revisados por SCI
- **THEN** su campo `reviewed` es falso y `source_id` identifica la fuente bibliográfica
