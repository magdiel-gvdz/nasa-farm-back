# Tasks

## 1. Aplicación

- [x] 1.1 Quitar Mangum de `app/main.py`, `pyproject.toml` y `requirements.txt`, y la prueba del adaptador en `tests/test_api.py`; verificar con `pytest -q` y `ruff check .`
- [x] 1.2 Eliminar `scripts/package_lambda.py` y `tests/test_package_lambda.py`, y el paso del paquete Lambda en `check.yml`; verificar que `pytest -q` y `actionlint` pasan

## 2. Despliegue

- [x] 2.1 En `infrastructure.yml`, tras asumir el rol: iniciar sesión en ECR, comprobar si existe la etiqueta del SHA y, si no, construir y publicar la imagen; verificar en la ejecución del PR que la imagen aparece en ECR
- [x] 2.2 Pasar `TF_VAR_image_tag` (SHA de la cabecera del PR o del commit de `main`) y `TF_VAR_ecr_repository_url` (variable `ECR_REPOSITORY_URL`), y quitar el paso "Package API"; verificar que el plan del workflow muestra la imagen esperada
- [x] 2.3 Pasar a Terraform las variables de DATA desde variables de repositorio con valores por defecto, incluida `DATA_PROVIDER`; verificar en el resumen del job que se imprimen entorno, URL y proveedor de datos
- [x] 2.4 Adaptar la prueba de humo a la nueva salida `api_url` con reintentos durante 2 minutos; verificar que el job falla si se fuerza un entorno distinto en la aserción

## 3. Limpieza

- [ ] 3.1 Actualizar `destroy-preview` y `cleanup-preview.yml` con las variables obligatorias nuevas (valores de relleno válidos para `image_tag`); verificar cerrando un PR de prueba que su entorno desaparece (`aws ecs` y `aws dynamodb` no listan recursos `pr-N`)
- [x] 3.2 Actualizar `docs/preview-lifecycle.md` con el nuevo ciclo (imagen, servicio, tiempos observados) y la recomendación de abrir los PR como borrador; verificar que los comandos citados existen en los workflows
