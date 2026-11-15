# Spec Delta

## Purpose

Define las identidades con las que CI despliega cada entorno y con las que la API se ejecuta, y los límites que impiden que un entorno afecte a otro o exceda sus permisos.

## ADDED Requirements

### Requirement: Repositorio de imágenes compartido
El bootstrap SHALL crear un único repositorio privado de imágenes de contenedor con etiquetas inmutables, escaneo al publicar y expiración automática de imágenes antiguas, y SHALL exponer su URL como salida.

#### Scenario: Salida disponible
- **WHEN** se aplica el bootstrap
- **THEN** la salida `ecr_repository_url` contiene la URL del repositorio

#### Scenario: Etiqueta repetida
- **WHEN** se publica una imagen con una etiqueta que ya existe
- **THEN** el repositorio rechaza la publicación

### Requirement: Despliegue acotado al propio entorno
Cada rol de despliegue SHALL poder publicar imágenes y gestionar únicamente el servicio de contenedor, la tabla, los registros y los roles IAM cuyos nombres correspondan al patrón de su entorno.

#### Scenario: Preview no toca dev
- **WHEN** el rol de preview intenta modificar o borrar un recurso con prefijo `nasa-farm-dev`
- **THEN** AWS deniega la operación

#### Scenario: Preview gestiona su entorno
- **WHEN** el rol de preview crea el servicio, la tabla y los roles de `nasa-farm-pr-12`
- **THEN** las operaciones se permiten

### Requirement: Límite de permisos de la API
El rol con el que se ejecuta la API MUST llevar un límite de permisos que solo permita: su tabla y su bucket, lectura de `gold/` en el lake de DATA, consultas en el workgroup de Athena de DATA con su bucket de resultados, lectura del catálogo de Glue y del parámetro SSM de versión de datos, invocación de modelos en Bedrock y escritura de registros.

#### Scenario: Política excesiva sin efecto
- **WHEN** un cambio de Terraform añade al rol de la API una política que permite `iam:*` o escritura en el lake
- **THEN** esas acciones siguen denegadas por el límite de permisos

#### Scenario: Rol sin límite
- **WHEN** el rol de despliegue intenta crear el rol de la API sin el límite de permisos
- **THEN** AWS deniega la creación

### Requirement: Roles de plataforma con políticas fijas
El rol de despliegue SHALL poder adjuntar a los roles de ejecución y de infraestructura del servicio solo las políticas administradas de AWS previstas para ese uso, y MUST NOT poder darles políticas en línea.

#### Scenario: Política no prevista
- **WHEN** el rol de despliegue intenta adjuntar `AdministratorAccess` a un rol de ejecución
- **THEN** AWS deniega la operación

### Requirement: Permisos de transición
Mientras exista algún entorno con Lambda y API Gateway, los roles de despliegue SHALL conservar los permisos necesarios para destruirlos.

#### Scenario: Migración de dev
- **WHEN** Terraform aplica en `dev` un plan que elimina la función Lambda y la API HTTP
- **THEN** la eliminación se completa sin errores de acceso

### Requirement: Acceso efectivo a DATA
El acceso de la API SHALL resultar de una política que conceda las operaciones y una permissions boundary que las permita sobre los mismos recursos. El bootstrap SHALL ampliar la boundary; el stack de entorno SHALL conceder los permisos mediante `fieldshift-gold-read` o una política equivalente acotada a los recursos configurados. Ambos SHALL permitir consultas en el workgroup, lectura de Glue gold y S3 `gold/*`, lectura/escritura de resultados de Athena y lectura del parámetro SSM exacto, en `DATA_REGION`. MUST NOT conceder escritura en el lake, modificación del catálogo ni actualización de SSM. El bucket del entorno y el lake compartido de DATA SHALL ser recursos distintos; destruir un preview MUST NOT destruir recursos de DATA.

#### Scenario: Acceso con el rol real de la API
- **WHEN** están aplicados bootstrap y entorno y DATA ha publicado una versión válida
- **THEN** el rol de la tarea puede leer el parámetro SSM y ejecutar SELECT en las vistas publicadas con el workgroup configurado

#### Scenario: Boundary sin concesión
- **WHEN** la boundary permite DATA pero ninguna política del rol concede esas operaciones
- **THEN** el acceso sigue denegado y la comprobación de integración detecta la configuración incompleta
