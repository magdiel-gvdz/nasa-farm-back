# Spec Delta

## Purpose

Da a la API acceso de solo lectura a los datos agroclimáticos por celda que publica DATA, con una única forma de consulta que no depende de dónde estén almacenados.

## ADDED Requirements

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
