# fields Specification

## Purpose
Permite a un cliente registrar, consultar, editar y borrar sus geocercas e invernaderos, que son la base de todos los cálculos del producto.

## Requirements

### Requirement: Alta de geocerca
`POST /api/v1/fields` SHALL crear una geocerca con nombre, tipo y geometría, y SHALL responder `201` con su identificador, área en hectáreas, centroide, celda y zona asignadas y fecha de creación.

#### Scenario: Alta correcta
- **WHEN** un cliente envía una geocerca válida dentro de una zona cubierta
- **THEN** la respuesta es `201` con un `id` que empieza por `fld_`, `cell_id`, `zone_id`, `area_ha` mayor que 0 y `profile_status` igual a `ready`

#### Scenario: Invernadero sin datos de estructura
- **WHEN** se envía `kind` igual a `greenhouse` sin el objeto `greenhouse`
- **THEN** la respuesta es `422` con `error.code` igual a `validation_error`

### Requirement: Aislamiento por cliente
La API MUST devolver y modificar únicamente las geocercas creadas con el mismo `X-Client-Id` de la petición.

#### Scenario: Geocerca de otro cliente
- **WHEN** el cliente B pide, edita o borra una geocerca creada por el cliente A
- **THEN** la respuesta es `404` con `error.code` igual a `not_found`

#### Scenario: Listado
- **WHEN** el cliente A lista sus geocercas
- **THEN** la lista contiene solo las suyas, de la más reciente a la más antigua

### Requirement: Edición parcial
`PATCH /api/v1/fields/{id}` SHALL modificar solo los campos enviados entre nombre, geometría, rotación actual, riego, ganado y datos de invernadero. Si cambia la geometría, la API SHALL recalcular área, centroide, celda y zona.

#### Scenario: Declarar la rotación actual
- **WHEN** se envía solo `current_rotation`
- **THEN** la geocerca conserva nombre y geometría y devuelve la rotación nueva

#### Scenario: Mover la geocerca fuera de cobertura
- **WHEN** se envía una geometría fuera de las zonas cubiertas
- **THEN** la respuesta es `422` con `error.code` igual a `out_of_region` y la geocerca no cambia

### Requirement: Borrado
`DELETE /api/v1/fields/{id}` SHALL eliminar la geocerca y responder `204`; una segunda llamada SHALL responder `404`.

#### Scenario: Borrado y consulta posterior
- **WHEN** se borra una geocerca y después se consulta por su `id`
- **THEN** el borrado responde `204` y la consulta responde `404`

### Requirement: Persistencia
Las geocercas SHALL conservarse tras reiniciar o redesplegar la API en un entorno con tabla configurada.

#### Scenario: Reinicio del servicio
- **WHEN** se crea una geocerca, se reinicia el contenedor y se lista
- **THEN** la geocerca sigue en la lista

### Requirement: Tope por cliente
La API SHALL rechazar el alta cuando el cliente ya tiene 50 geocercas.

#### Scenario: Tope alcanzado
- **WHEN** un cliente con 50 geocercas envía otra
- **THEN** la respuesta es `409` con `error.code` igual a `field_limit_reached`
