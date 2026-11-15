# Tasks

## 1. Modelos

- [x] 1.1 Crear `app/api/schemas/common.py` con `Source` (incluye `data_class`), `Gap`, `Confidence`, `Scenario` y el sobre de error; verificar con una prueba que serializa cada uno
- [x] 1.2 Crear `app/api/schemas/fields.py` (`FieldCreate`, `FieldUpdate`, `Field` con `cell_id`, `zone_id`, `area_ha`, `centroid`, `country`, `admin`, `created_at`) y `crops.py` (`Crop` según handoff §6.1 más `heat_critical_c`); verificar con pruebas de validación de un ejemplo válido y uno inválido por modelo
- [x] 1.3 Crear `app/api/schemas/profile.py` con `FieldProfile` (clima mensual, `risk_calendar` de 36 decenas, suelo, agua, vegetación, `sources`, `gaps`; secciones opcionales anulables); verificar que el validador rechaza un calendario que no tenga 36 decenas únicas
- [x] 1.4 Crear `app/api/schemas/suitability.py` (detalle y matriz) y `rotations.py` (petición, estrategia con `metrics`, `scores`, `why`, `evidence`, `benefits`, `gaps`, `risks_local_review`, y respuesta); verificar con pruebas de validación

## 2. Rutas y respuestas fijas

- [x] 2.1 Crear un archivo JSON por endpoint en `app/api/fixtures/` para una celda de Saltillo, con valores plausibles y al menos 3 estrategias de rotación; verificar con una prueba parametrizada que cada archivo valida contra su modelo
- [x] 2.2 Crear los enrutadores bajo `/api/v1` (un módulo por recurso) que devuelven la respuesta fija con `X-Fieldshift-Mock: 1` y registrarlos en `app/main.py`; mover `sources` a `/api/v1/sources`; verificar con `tests/api/test_contract.py` que cada ruta responde `200` (o `201`) y valida contra su modelo
- [x] 2.3 Verificar con una prueba que ninguna clave de ninguna respuesta fija contiene mayúsculas o guiones

## 3. Publicación del contrato

- [x] 3.1 Crear `scripts/export_openapi.py` que escribe `contracts/openapi.json` de forma determinista y generar el archivo; verificar que dos ejecuciones seguidas no producen diferencias
- [x] 3.2 Añadir a `check.yml` un paso que regenera el documento y falla si `git diff --exit-code contracts/openapi.json` detecta cambios; verificar con `actionlint` y con la ejecución del workflow
- [x] 3.3 Escribir `docs/api-contract.md` con las cinco diferencias respecto al handoff y un ejemplo de llamada por endpoint; avisar al frontend con el enlace al preview; verificar que los ejemplos funcionan contra el preview con `curl`
