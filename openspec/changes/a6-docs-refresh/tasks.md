# Tasks

## 1. Documentación

- [ ] 1.1 Reescribir en `README.md` la descripción, el diagrama, la tabla de entornos, la sección de validación y la de estructura para ECS Express Mode, ECR y DynamoDB; verificar que cada comando documentado se ejecuta tal como está escrito
- [x] 1.2 Sustituir la sección "Data lake" por la relación con el lake de DATA (vistas de Athena, parámetro SSM, variable `DATA_PROVIDER`) con enlace a `docs/fuentes_de_datos.md`; verificar que los nombres de variables coinciden con `infra/environment/variables.tf`
- [x] 1.3 Actualizar la sección de límites: sin límite de peticiones de API Gateway, coste por entorno encendido, previews en borrador; verificar contra `docs/preview-lifecycle.md`

## 2. Contexto de OpenSpec

- [x] 2.1 Actualizar `context` en `openspec/config.yaml` (contenedor en ECS Express Mode, DynamoDB, lectura de gold, validación con construcción de imagen, alcance con motores y chat); verificar con `openspec validate --all --strict`
- [ ] 2.2 Buscar `mangum`, `lambda` y `manifest` en el repositorio y eliminar las referencias obsoletas, incluido `contracts/data-manifest.schema.json` si no tiene usos; verificar con la búsqueda y con `pytest -q`
