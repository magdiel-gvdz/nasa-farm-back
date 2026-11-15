# Tasks

## 1. Motor

- [x] 1.1 Implementar en `app/engines/greenhouse.py` la extracción de máximos anuales de `wind_max_ms` (años con al menos 360 días) y el ajuste de Gumbel por momentos (`β = √6·σ/π`, `μ = media − 0.5772·β`); verificar con la prueba de la muestra simulada
- [x] 1.2 Implementar niveles de retorno a 10, 25 y 50 años (`x_T = μ − β·ln(−ln(1 − 1/T))`), conversión a km/h, ráfaga estimada con factor configurable y probabilidad anual de superar la resistencia; verificar con un caso calculado a mano
- [x] 1.3 Implementar el estado (`ok` por debajo del 2 % anual, `warn` hasta el 10 %, `bad` por encima; cortes en `config/engine.yaml`), los meses de mayor riesgo y las reglas de fiabilidad por años disponibles; verificar con pruebas de 10 años, de 4 años y de resistencia no declarada

## 2. Endpoint

- [x] 2.1 Añadir los modelos de respuesta y `GET /fields/{id}/greenhouse` con `not_a_greenhouse`, `daily_unavailable`, secciones no cubiertas en `null` y vacíos y notas es/en; verificar con pruebas de API de cada caso
- [x] 2.2 Añadir recomendaciones por plantillas (revisar anclajes antes de los meses de riesgo, validar con el fabricante); regenerar `contracts/openapi.json`; verificar con la prueba de contrato
- [x] 2.3 Configurar el respaldo de POWER para pedir desde 1991 cuando el origen de la serie sea `power_live`, y verificar en un preview que un invernadero de Saltillo devuelve confianza distinta de `low`
  - En `pr-19` con datos reales: invernadero de Saltillo con 35 años de registro, confianza `medium` y estado `ok`
  - Configurado: el respaldo POWER pide desde 1991. Los previews usan datos sintéticos (10 años, confianza `low`); con la vista diaria real de DATA (1991-2025) hay 35 años. Verificación en preview pendiente de activar Athena (`c2`). Con la serie real de DATA, leída en local, un invernadero de Saltillo con 100 km/h da 35 años, confianza `medium`, niveles de 56.4, 61.2 y 64.7 km/h, probabilidad anual 0.53 % y estado `ok`
- [x] 2.4 Añadir la sección de invernadero a `docs/engines.md` con fórmulas, cortes y límites; verificar que los cortes coinciden con `config/engine.yaml`
