# Spec Delta

## Purpose

Define los recursos de AWS que componen un entorno de la API de Field Shift (servicio de contenedor, estado, almacenamiento y permisos) y cómo se crean y destruyen para `dev` y para cada preview.

## ADDED Requirements

### Requirement: Servicio de contenedor por entorno
Cada entorno SHALL exponer la API en una URL HTTPS pública servida por un servicio de contenedor que ejecuta la imagen del repositorio compartido identificada por una etiqueta inmutable recibida como entrada.

#### Scenario: Entorno nuevo
- **WHEN** se aplica el stack para `pr-12` con una etiqueta de imagen existente
- **THEN** la salida `api_url` es una URL HTTPS y `GET <api_url>/health` responde `200` con `environment` igual a `pr-12`

#### Scenario: Imagen inexistente
- **WHEN** se aplica el stack con una etiqueta que no existe en el repositorio
- **THEN** el apply termina con error y no informa de un despliegue correcto

### Requirement: Despliegue condicionado a la salud
El servicio SHALL comprobar `GET /health` del contenedor y el despliegue MUST fallar si el contenedor no llega a estar sano.

#### Scenario: Contenedor que no arranca
- **WHEN** la imagen desplegada no responde en `/health`
- **THEN** el apply falla y la versión anterior del servicio, si existe, sigue atendiendo

### Requirement: Estado persistente por entorno
Cada entorno SHALL tener una tabla propia de clave `client_id` y `sk`, con facturación por petición. La tabla de `dev` MUST estar protegida contra borrado y las de preview MUST destruirse con su entorno.

#### Scenario: Destrucción de un preview
- **WHEN** se destruye el stack de `pr-12`
- **THEN** no quedan servicio, tabla, bucket, roles ni grupos de registros de `pr-12`

### Requirement: Configuración entregada al contenedor
El stack SHALL entregar al contenedor, como variables de entorno, el nombre del entorno, los orígenes CORS, su tabla, su bucket, el proveedor de datos, la región y los nombres de los recursos de DATA, y el identificador del modelo de lenguaje.

#### Scenario: Cambio de proveedor de datos
- **WHEN** se aplica el stack con el proveedor de datos `athena` en lugar de `fixture`
- **THEN** el contenedor arranca con `DATA_PROVIDER=athena` sin cambios en la imagen

### Requirement: Mínimo privilegio de la API
El rol de la API SHALL poder leer y escribir solo su tabla y los prefijos `uploads/` y `cache/` de su bucket, y leer los recursos de DATA; MUST NOT poder escribir en el lake ni acceder a recursos de otro entorno.

#### Scenario: Aislamiento entre entornos
- **WHEN** la API de `pr-12` intenta leer la tabla de `dev`
- **THEN** AWS deniega la operación

### Requirement: Retiro de la plataforma anterior
Tras aplicar el stack, el entorno MUST NOT contener la función Lambda ni la API HTTP de API Gateway anteriores.

#### Scenario: Migración de un entorno existente
- **WHEN** se aplica el stack sobre un entorno que tenía Lambda y API Gateway
- **THEN** ambos recursos y sus grupos de registros quedan eliminados y el bucket del entorno conserva sus objetos

### Requirement: Acceso efectivo a DATA
El acceso de la API SHALL resultar de una política que conceda las operaciones y una permissions boundary que las permita sobre los mismos recursos. El bootstrap SHALL ampliar la boundary; el stack de entorno SHALL conceder los permisos mediante `fieldshift-gold-read` o una política equivalente acotada a los recursos configurados. Ambos SHALL permitir consultas en el workgroup, lectura de Glue gold y S3 `gold/*`, lectura/escritura de resultados de Athena y lectura del parámetro SSM exacto, en `DATA_REGION`. MUST NOT conceder escritura en el lake, modificación del catálogo ni actualización de SSM. El bucket del entorno y el lake compartido de DATA SHALL ser recursos distintos; destruir un preview MUST NOT destruir recursos de DATA.

#### Scenario: Acceso con el rol real de la API
- **WHEN** están aplicados bootstrap y entorno y DATA ha publicado una versión válida
- **THEN** el rol de la tarea puede leer el parámetro SSM y ejecutar SELECT en las vistas publicadas con el workgroup configurado

#### Scenario: Boundary sin concesión
- **WHEN** la boundary permite DATA pero ninguna política del rol concede esas operaciones
- **THEN** el acceso sigue denegado y la comprobación de integración detecta la configuración incompleta
