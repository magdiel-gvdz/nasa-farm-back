# deploy-pipeline Specification

## Purpose
Define cómo un commit del repositorio se convierte en un entorno desplegado y verificado, y cómo se limpian los entornos efímeros de los PR.

## Requirements

### Requirement: Imagen publicada por commit
El pipeline SHALL construir la imagen de la API y publicarla en el repositorio compartido con el SHA del commit como etiqueta antes de aplicar la infraestructura, y SHALL desplegar exactamente esa etiqueta.

#### Scenario: Despliegue de un PR
- **WHEN** se actualiza un PR interno que no es borrador
- **THEN** existe en el repositorio una imagen etiquetada con el SHA de la cabecera del PR y el entorno `pr-N` ejecuta esa imagen

#### Scenario: Reejecución del mismo commit
- **WHEN** el workflow se vuelve a ejecutar para un commit cuya imagen ya está publicada
- **THEN** el pipeline reutiliza la imagen existente y no falla por la etiqueta repetida

### Requirement: Verificación tras el despliegue
El pipeline SHALL consultar `/health` en la URL del entorno desplegado y MUST fallar si la respuesta no es correcta o informa de otro entorno.

#### Scenario: Entorno equivocado
- **WHEN** `/health` devuelve un `environment` distinto del entorno desplegado
- **THEN** el job de despliegue falla

### Requirement: Reglas de activación conservadas
El pipeline MUST NOT desplegar PR de forks ni PR en borrador, MUST NOT cancelar un apply en curso y SHALL desplegar `dev` solo desde `main`.

#### Scenario: PR en borrador
- **WHEN** se abre o actualiza un PR en borrador
- **THEN** se ejecutan las comprobaciones pero no se publica imagen ni se crea el entorno

### Requirement: Limpieza de previews
Al cerrarse un PR, el pipeline SHALL destruir todos los recursos de su entorno; el workflow manual de limpieza SHALL poder hacerlo para un PR cerrado cuyo borrado automático falló.

#### Scenario: PR fusionado
- **WHEN** se fusiona un PR con entorno `pr-N`
- **THEN** el servicio, la tabla, el bucket y los roles de `pr-N` quedan destruidos

### Requirement: Aplicación sin adaptador de Lambda
La aplicación MUST NOT depender de bibliotecas ni puntos de entrada específicos de AWS Lambda.

#### Scenario: Dependencias de ejecución
- **WHEN** se instalan las dependencias de ejecución
- **THEN** `mangum` no está entre ellas y `app.main` no exporta `handler`
