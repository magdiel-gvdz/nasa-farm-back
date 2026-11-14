# Spec Delta

## Purpose

Da a la API acceso de solo lectura a los datos agroclimáticos por celda que publica DATA, con una única forma de consulta que no depende de dónde estén almacenados.

## ADDED Requirements

### Requirement: Lectura exclusiva de las vistas publicadas
Con `DATA_PROVIDER=athena`, la API SHALL leer únicamente las vistas `v_cells`, `v_cell_profile`, `v_cell_indicators`, `v_cell_year`, `v_cell_soil` y `v_sources` de la base de datos de DATA, y MUST NOT escribir en el lake ni consultar tablas internas del pipeline.

#### Scenario: Consultas emitidas
- **WHEN** la API completa una carga de datos
- **THEN** todas las consultas emitidas son `SELECT` sobre vistas cuyo nombre empieza por `v_`

### Requirement: Datos en memoria
La API SHALL cargar los datos publicados completos al arrancar y SHALL responder a las peticiones desde memoria, sin consultar Athena por petición.

#### Scenario: Petición tras la carga
- **WHEN** un cliente pide el perfil de una geocerca después de la carga inicial
- **THEN** la respuesta no provoca ninguna consulta nueva a Athena

#### Scenario: Arranque
- **WHEN** el contenedor arranca y la carga inicial está en curso
- **THEN** `GET /health` responde `200` y `GET /ready` responde `503` hasta que la carga termina

### Requirement: Actualización al publicar DATA
La API SHALL comprobar la versión de datos publicada al menos cada 5 minutos y SHALL recargar cuando cambie, sin reinicio ni redespliegue.

#### Scenario: Nueva publicación
- **WHEN** DATA publica una versión nueva y actualiza el parámetro de versión
- **THEN** en un máximo de 10 minutos `GET /ready` informa la versión nueva y las respuestas usan sus valores

#### Scenario: Versión sin cambios
- **WHEN** la comprobación periódica encuentra la misma versión
- **THEN** no se ejecuta ninguna consulta de datos

### Requirement: Tolerancia a fallos de carga
Si una recarga falla o sus datos no superan la validación, la API SHALL seguir sirviendo la última versión cargada correctamente. Si nunca hubo una carga correcta, los endpoints que dependen de datos SHALL responder `503` con `error.code` igual a `data_unavailable`.

#### Scenario: Recarga fallida
- **WHEN** Athena devuelve un error durante una recarga
- **THEN** las respuestas siguen usando la versión anterior y `GET /ready` sigue en `200` con esa versión

#### Scenario: Sin datos desde el arranque
- **WHEN** la carga inicial falla
- **THEN** `GET /api/v1/fields/{id}/profile` responde `503` con `error.code` igual a `data_unavailable`

### Requirement: Validación de lo publicado
La API SHALL verificar que cada vista contiene las columnas que usa y que hay al menos una celda antes de aceptar una carga; las columnas adicionales MUST ignorarse.

#### Scenario: Columna obligatoria ausente
- **WHEN** una versión publicada no incluye `frost_prob` en `v_cell_profile`
- **THEN** la carga se rechaza y el registro indica la vista y la columna que falta

#### Scenario: Columna nueva
- **WHEN** una versión publicada añade una columna desconocida
- **THEN** la carga se acepta
