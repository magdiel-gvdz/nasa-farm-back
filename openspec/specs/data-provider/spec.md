# data-provider Specification

## Purpose
Da a la API acceso de solo lectura a los datos agroclimáticos por celda que publica DATA, con una única forma de consulta que no depende de dónde estén almacenados.

## Requirements

### Requirement: Proveedor seleccionable
La API SHALL obtener todos los datos agroclimáticos a través de un proveedor elegido por la variable `DATA_PROVIDER`, y el comportamiento de los endpoints MUST NOT depender de cuál esté activo salvo por los valores devueltos.

#### Scenario: Valor por defecto
- **WHEN** la API arranca sin `DATA_PROVIDER`
- **THEN** usa el proveedor de datos sintéticos y `GET /ready` responde `200`

#### Scenario: Valor desconocido
- **WHEN** `DATA_PROVIDER` tiene un valor no admitido
- **THEN** la API no arranca e informa del valor inválido en el registro

### Requirement: Conjuntos de datos disponibles
El proveedor SHALL entregar, por celda: sus atributos, las 36 filas de climatología por decena, los indicadores por año y decena, las series anuales y el perfil de suelo por profundidad; y de forma global, la lista de celdas, las zonas y las fuentes, con los nombres de columna y unidades del contrato de DATA.

#### Scenario: Climatología completa
- **WHEN** se pide la climatología de una celda existente
- **THEN** se obtienen 36 filas con `decade` de 1 a 36

#### Scenario: Celda inexistente
- **WHEN** se pide cualquier dato de una celda que no existe
- **THEN** el proveedor indica que la celda es desconocida y la API puede traducirlo a `out_of_region` o `not_found`

### Requirement: Ausencia de dato explícita
El proveedor MUST representar un dato faltante como valor nulo y MUST NOT entregar valores de relleno como `-999` o `-9999`.

#### Scenario: Indicador sin NDVI
- **WHEN** una celda no tiene todavía datos de NDVI
- **THEN** `ndvi_mean` y `bare_prob` son nulos

### Requirement: Datos sintéticos de referencia
El proveedor de datos sintéticos SHALL ser determinista y SHALL incluir al menos una celda de la zona `coah-sureste` y una de `coah-laguna`, con diez años de indicadores, climatología, suelo a tres profundidades y fuentes marcadas como sintéticas.

#### Scenario: Reproducibilidad
- **WHEN** se arranca la API dos veces con datos sintéticos y se pide la misma celda
- **THEN** las respuestas son idénticas

#### Scenario: Marca de dato sintético
- **WHEN** se consulta `GET /api/v1/sources` con datos sintéticos
- **THEN** cada fuente indica que su clase de dato es sintética y `GET /ready` informa `data_version` igual a `fixture`

### Requirement: Fuentes desde el proveedor
`GET /api/v1/sources` SHALL devolver las fuentes del proveedor activo con identificador, nombre, organización, producto, URL, resolución, periodo, licencia y clase de dato.

#### Scenario: Atribución
- **WHEN** se consulta `GET /api/v1/sources`
- **THEN** cada elemento tiene `id`, `organization`, `resolution`, `period`, `license` y `data_class` no vacíos

### Requirement: Lectura exclusiva de las vistas publicadas
Con `DATA_PROVIDER=athena`, la API SHALL leer únicamente las vistas `v_cells`, `v_cell_profile`, `v_cell_indicators`, `v_cell_year`, `v_cell_soil` y `v_sources` para la carga en memoria, y `v_cell_daily` bajo demanda por celda según `c4-daily-series`, de la base de datos de DATA, y MUST NOT escribir en el lake ni consultar tablas internas del pipeline.

#### Scenario: Consultas emitidas
- **WHEN** la API completa una carga de datos
- **THEN** todas las consultas emitidas son `SELECT` sobre vistas cuyo nombre empieza por `v_`

### Requirement: Datos en memoria
La API SHALL cargar los datos publicados completos al arrancar y SHALL responder a las peticiones desde memoria, sin consultar Athena por petición para esos seis conjuntos. La serie diaria queda fuera de la instantánea y se consulta bajo demanda según `c4-daily-series`.

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

### Requirement: Consultas compatibles con los permisos de DATA
El ejecutor SHALL usar SELECT ordinarios en el workgroup configurado, con clientes en `DATA_REGION`, sin reutilización de resultados, CTAS ni UNLOAD. Con `awswrangler` SHALL fijar `ctas_approach=False` y `unload_approach=False`. La ubicación y el cifrado de resultados SHALL provenir del workgroup, sin sobrescribir OutputLocation ni crear tablas.

#### Scenario: Rol de solo lectura
- **WHEN** se cargan las vistas con `fieldshift-gold-read` y una boundary compatible
- **THEN** las consultas terminan sin crear tablas, modificar el catálogo ni escribir en el lake

### Requirement: Publicación disponible
La existencia de recursos Terraform MUST NOT considerarse una publicación lista. El valor SSM inicial `none` SHALL significar ausencia de publicación y MUST NOT aceptarse como versión. El proveedor SHALL esperar y reintentar periódicamente sin consultar vistas mientras ese valor siga vigente; si existe una instantánea válida SHALL conservarla.

#### Scenario: Infraestructura recién creada
- **WHEN** SSM vale `none` y no hubo una carga válida
- **THEN** `/health` responde `200`, `/ready` responde `503` y los endpoints dependientes responden `503` con `data_unavailable`

#### Scenario: Primera publicación posterior al arranque
- **WHEN** DATA publica las vistas y una versión válida
- **THEN** el proveedor la detecta y pasa a estar listo tras cargarla y validarla

### Requirement: Consistencia de publicación
Cada instantánea aceptada SHALL contener datos de una única publicación identificada por `data_version`. Antes de activar Athena, BE y DATA MUST acordar e implementar un protocolo que impida aceptar vistas de versiones distintas durante su recreación. Obtener el mismo SSM antes y después de la carga MUST NOT considerarse garantía suficiente: las vistas pueden cambiar antes de actualizar el parámetro. Sin ese protocolo verificado, la activación SHALL permanecer en `fixture`.

#### Scenario: Publicación durante la carga
- **WHEN** DATA cambia las vistas entre consultas de una carga
- **THEN** el protocolo impide aceptar una instantánea mezclada; la API conserva la última válida o permanece no lista y reintenta
