# Spec Delta

## Purpose

Permite al agricultor incorporar el análisis de suelo de su laboratorio al perfil de su geocerca, sustituyendo estimaciones zonales por mediciones de su parcela.

## ADDED Requirements

### Requirement: Subida del análisis
`POST /api/v1/fields/{id}/soil-report` SHALL aceptar un archivo PDF, JPG o PNG de hasta 10 MB y SHALL rechazar otros tipos con `415` y tamaños mayores con `413`.

#### Scenario: Archivo admitido
- **WHEN** un cliente sube un PDF de 2 MB para una geocerca suya
- **THEN** la respuesta es `200` con los valores extraídos

#### Scenario: Tipo no admitido
- **WHEN** se sube un archivo `.docx`
- **THEN** la respuesta es `415` con `error.code` igual a `unsupported_file_type`

### Requirement: Extracción estructurada
El sistema SHALL extraer del documento, cuando estén presentes: laboratorio, fecha de muestreo, profundidad, materia orgánica, nitrógeno, fósforo, potasio, pH, conductividad eléctrica, capacidad de intercambio catiónico y textura, con sus unidades normalizadas, y SHALL listar los campos que no pudo leer.

#### Scenario: Análisis legible
- **WHEN** se sube un análisis con pH 8.1 y materia orgánica 1.9 %
- **THEN** `extracted.ph` es 8.1, `extracted.om_pct` es 1.9 y `unreadable_fields` no los contiene

#### Scenario: Documento que no es un análisis de suelo
- **WHEN** se sube una factura
- **THEN** la respuesta es `422` con `error.code` igual a `not_a_soil_report` y la geocerca no cambia

### Requirement: Validación de valores
El sistema MUST descartar cualquier valor extraído fuera de un rango plausible para su magnitud y SHALL incluirlo en `unreadable_fields` con el motivo.

#### Scenario: pH imposible
- **WHEN** el valor extraído de pH es 81
- **THEN** `extracted.ph` es `null` y `unreadable_fields` contiene `ph` con el motivo `out_of_range`

### Requirement: Actualización del perfil
Cuando al menos un valor es aceptado, el perfil de la geocerca SHALL mostrar los valores de laboratorio en `soil.lab` con su fecha, la confianza del suelo SHALL ser alta, el vacío de análisis de laboratorio SHALL desaparecer y la fuente SHALL identificarse como análisis del agricultor.

#### Scenario: Perfil tras la subida
- **WHEN** se consulta el perfil después de una subida con valores aceptados
- **THEN** `soil.lab` contiene esos valores, `soil.confidence` es `high` y `gaps` no contiene el vacío de análisis de laboratorio

### Requirement: Uso en la aptitud
El motor de aptitud SHALL usar el pH de laboratorio en lugar del estimado cuando exista, e indicarlo en el detalle del factor suelo.

#### Scenario: pH de laboratorio distinto del estimado
- **WHEN** el pH estimado de la zona es 7.9 y el de laboratorio es 6.8
- **THEN** el factor `soil` se evalúa con 6.8 y su detalle cita el análisis de laboratorio

### Requirement: Custodia del archivo
El archivo SHALL guardarse bajo un prefijo propio del cliente en el almacenamiento privado del entorno, y MUST NOT ser accesible mediante URL pública ni por otros clientes.

#### Scenario: Otro cliente
- **WHEN** otro cliente consulta el perfil o sube un análisis indicando la geocerca ajena
- **THEN** la respuesta es `404`

### Requirement: Modelo no disponible
Si el modelo de lenguaje no está disponible o el chat está desactivado, el endpoint SHALL responder `503` y MUST NOT modificar la geocerca.

#### Scenario: Chat desactivado
- **WHEN** `CHAT_ENABLED` es falso y se sube un análisis
- **THEN** la respuesta es `503` con `error.code` igual a `chat_disabled`
