# Tasks

## 1. Repositorio

- [ ] 1.1 Definir en `app/store/base.py` la interfaz de repositorio (`put`, `get`, `list_prefix`, `delete`, `count_prefix` por `client_id` y `sk`) y la implementación en memoria; verificar con `tests/store/test_repository.py`
- [ ] 1.2 Implementar el repositorio DynamoDB en `app/store/dynamodb.py` (documento JSON más atributos `cell_id`, `kind`, `created_at`) y la selección por `APP_TABLE` en la configuración; verificar ejecutando la misma batería de pruebas contra DynamoDB simulado
- [ ] 1.3 Añadir generación de identificadores `fld_` + ULID; verificar con una prueba que dos identificadores consecutivos son distintos y ordenables

## 2. Rutas

- [ ] 2.1 Definir la interfaz `locate(geometry)` con una implementación provisional (celda de Saltillo) inyectable; verificar que las pruebas pueden sustituirla
- [ ] 2.2 Implementar `POST`, `GET` (lista y detalle), `PATCH` y `DELETE` de `/fields` sobre el repositorio, quitando `X-Fieldshift-Mock` de esas rutas; verificar con pruebas de alta, listado ordenado, edición parcial, borrado y `404` posterior
- [ ] 2.3 Implementar el aislamiento por cliente y el tope de 50; verificar con pruebas de dos `X-Client-Id` distintos y del alta número 51
- [ ] 2.4 Validar que `greenhouse` es obligatorio cuando `kind` es `greenhouse` y que la geometría fuera de región deja intacta la geocerca en `PATCH`; verificar con pruebas

## 3. Integración

- [ ] 3.1 Regenerar `contracts/openapi.json` si cambió algún modelo y actualizar `docs/api-contract.md` con el ciclo de vida de una geocerca y la advertencia de que `X-Client-Id` no es autenticación; verificar que la comprobación del contrato pasa en CI
- [ ] 3.2 En un preview con tabla real, crear una geocerca, forzar un nuevo despliegue y listar; verificar que persiste
