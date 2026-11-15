# Tasks

## 1. Geocercas

- [x] 1.1 Definir en `demo/fields.json` las dos geocercas (polígono dentro de una celda publicada, nombre, rotación actual, riego, ganado si aplica) y las prioridades de cada historia; verificar con el servicio de localización que cada una cae en la zona esperada
- [x] 1.2 Crear `scripts/seed_demo.py` que las da de alta de forma idempotente contra una URL con un `X-Client-Id` fijo documentado; verificar ejecutándolo dos veces contra un preview sin duplicados
  - Verificado con pruebas (`tests/scripts/test_seed_demo.py`); contra el preview del PR se anota en el PR

## 2. Revisión agronómica

- [ ] 2.1 Generar para cada geocerca perfil, matriz de aptitud, rotaciones y un escenario (+2 °C, −20 % de lluvia) y revisarlos con SCI: que la alternativa recomendada sea defendible, que las decenas vulnerables coincidan con el conocimiento local y que ningún texto prometa de más; verificar con la lista de observaciones de SCI adjunta al PR
  - Bloqueada: requiere al rol científico. Las observaciones previas están en `docs/demo-script.md` (veza sembrada en mayo; sorgo `suitable` con calor `bad`; sin margen)
- [ ] 2.2 Corregir catálogo, umbrales o textos según las observaciones y regenerar las instantáneas de `d5-engine-tests`; verificar que `pytest -q` pasa y que SCI aprueba el resultado
  - Bloqueada por 2.1

## 3. Guion

- [x] 3.1 Escribir `docs/demo-script.md` con el recorrido paso a paso (qué se muestra, qué llamada hay detrás, qué resultado se espera) y las frases sobre resolución zonal, vacíos de información y validación local; verificar siguiendo el guion completo contra `dev`
- [x] 3.2 Sembrar `dev` tras la última publicación de DATA y ejecutar `scripts/smoke_e2e.py --require-real` en ambas zonas; verificar que termina con código 0 y anotar la versión de datos usada en el guion
  - `dev` con datos reales (versión `2026111508`): `--require-real` termina con `OK` en `sureste` y `laguna` y las geocercas de la demo están sembradas
  - Bloqueada: `dev` sirve datos sintéticos hasta activar Athena (`c2` 4.1)
