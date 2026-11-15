# field-geolocation Specification

## Purpose
Valida la geometría que dibuja el agricultor y la sitúa en la malla común de análisis (celda de 9 km) y en las zonas piloto, de forma idéntica a como lo hace el pipeline de datos.

## Requirements

### Requirement: Validación de geometría
La API SHALL aceptar geometrías GeoJSON de tipo `Polygon` o `MultiPolygon` en WGS84 con anillos cerrados, coordenadas dentro de rango, como máximo 2,000 vértices y como máximo 10,000 hectáreas, y SHALL rechazar las demás con `422` y `error.code` igual a `invalid_geometry`.

#### Scenario: Anillo abierto
- **WHEN** el primer y el último punto de un anillo no coinciden
- **THEN** la respuesta es `422` con `error.code` igual a `invalid_geometry`

#### Scenario: Coordenadas invertidas
- **WHEN** una coordenada tiene latitud fuera de -90 a 90
- **THEN** la respuesta es `422` y `error.details` indica que el orden esperado es `[lon, lat]`

#### Scenario: Superficie excesiva
- **WHEN** el polígono mide más de 10,000 hectáreas
- **THEN** la respuesta es `422` con `error.code` igual a `invalid_geometry`

### Requirement: Área y centroide
La API SHALL calcular el área de la geocerca en hectáreas con un error menor al 1 % y su centroide en `[lon, lat]`.

#### Scenario: Cuadrado conocido
- **WHEN** se registra un cuadrado de 1 km de lado cerca de Saltillo
- **THEN** `area_ha` está entre 99 y 101 y el centroide cae dentro del cuadrado

### Requirement: Asignación de celda
La API SHALL asignar a cada geocerca la celda de la malla EASE-Grid 2.0 global de 9 km que contiene su centroide, con identificador `E9_r{fila:04d}_c{columna:04d}`, usando la misma proyección, origen y tamaño de celda que el pipeline de datos.

#### Scenario: Coincidencia con DATA
- **WHEN** se calcula la celda del centroide de cada una de las celdas publicadas por DATA
- **THEN** el identificador obtenido coincide con el de DATA en todos los casos

#### Scenario: Geocerca entre dos celdas
- **WHEN** un polígono se extiende sobre dos celdas
- **THEN** se asigna la celda del centroide y la respuesta lo indica con `cell_assignment` igual a `centroid`

### Requirement: Terreno fuera de cobertura
Cuando la celda asignada no pertenece a ninguna zona publicada, la API SHALL responder `422` con `error.code` igual a `out_of_region` y SHALL incluir en `error.details` las zonas disponibles con su nombre y recuadro.

#### Scenario: Polígono en otro estado
- **WHEN** se registra una geocerca en Nevada
- **THEN** la respuesta es `422` con `error.code` igual a `out_of_region` y `error.details.zones` lista las cuatro zonas de Coahuila

### Requirement: Contexto administrativo
La API SHALL devolver `country`, y `admin.state` a partir de la zona asignada; `admin.municipality` SHALL ser `null` cuando no pueda determinarse con certeza.

#### Scenario: Geocerca en el Sureste
- **WHEN** se registra una geocerca en la zona `coah-sureste`
- **THEN** `country` es `MX`, `admin.state` es `Coahuila` y `admin.municipality` es `null`
