# Spec Delta

## Purpose

Define cómo se empaqueta, configura y arranca la API de Field Shift como imagen de contenedor, de modo que cualquier plataforma de contenedores pueda ejecutarla sin adaptadores.

## ADDED Requirements

### Requirement: Imagen ejecutable de la API
El repositorio SHALL producir una imagen de contenedor que arranque la API HTTP escuchando en el puerto 8080 en todas las interfaces, sin requerir el entorno de ejecución de AWS Lambda.

#### Scenario: Arranque sin credenciales de AWS
- **WHEN** se ejecuta la imagen sin credenciales de AWS ni variables opcionales
- **THEN** `GET /health` en el puerto 8080 responde `200` con `status` igual a `ok` en menos de 10 segundos

### Requirement: Proceso sin privilegios
El contenedor MUST ejecutar la API con un usuario que no sea root.

#### Scenario: Usuario del proceso
- **WHEN** se consulta el identificador de usuario del proceso principal del contenedor
- **THEN** el identificador es distinto de 0

### Requirement: Configuración por variables de entorno
La imagen SHALL tomar toda su configuración de variables de entorno y MUST NOT contener secretos, credenciales ni archivos de estado de Terraform.

#### Scenario: Entorno informado en la salud
- **WHEN** el contenedor arranca con `ENVIRONMENT=pr-7`
- **THEN** `GET /health` devuelve `environment` igual a `pr-7`

#### Scenario: Contenido excluido de la imagen
- **WHEN** se lista el sistema de archivos de la imagen
- **THEN** no existen `.git`, `.venv`, `infra/`, `tests/` ni archivos `.env`

### Requirement: Apagado ordenado
El contenedor SHALL terminar al recibir `SIGTERM` en un máximo de 10 segundos, dejando terminar las peticiones en curso.

#### Scenario: Parada del contenedor
- **WHEN** la plataforma envía `SIGTERM` al contenedor
- **THEN** el proceso termina con código 0 en menos de 10 segundos

### Requirement: Construcción verificada en cada PR
Las comprobaciones automáticas de cada PR SHALL construir la imagen y verificar que responde en `/health`.

#### Scenario: Dockerfile roto
- **WHEN** un PR introduce un cambio que impide construir o arrancar la imagen
- **THEN** el workflow de comprobaciones falla
