# Tasks

## 1. Clima

- [x] 1.1 Implementar en `app/profile/monthly.py` la agregación de decenas a meses a partir de los indicadores por año y decena (fracción de años con evento, medias de días, totales de lluvia con P20 y P80, récords de las series anuales); verificar con una prueba del caso de 4 de 10 años y otra de un mes sin eventos
- [x] 1.2 Construir `climate.risk_calendar` desde la climatología por decena, con fecha de inicio de cada decena, umbrales y `vulnerable_reasons`; verificar con una prueba de 36 entradas y de una decena vulnerable
- [x] 1.3 Construir `climate.frost`, `rain`, `heat` y `wind` (viento desde las series anuales, en km/h) con sus `source_id` y años analizados; verificar con datos sintéticos de Saltillo que enero tiene mayor probabilidad de helada que julio

## 2. Suelo, agua y vegetación

- [x] 2.1 Construir `soil` (capas con media, P05 y P95, clase textural, materia orgánica estimada, `lab` nulo, confianza media); verificar con una prueba de tres profundidades
- [x] 2.2 Construir `water` (percentiles de humedad por mes, fuente usada según `sm_src`, ET0 y balance por mes, `groundwater` nulo) y `vegetation` (NDVI por mes, meses de suelo descubierto, nulo si no hay NDVI); verificar con pruebas con y sin NDVI

## 3. Procedencia y vacíos

- [x] 3.1 Implementar en `app/profile/gaps.py` las reglas de vacíos con mensajes es/en en el catálogo de `app/i18n.py`; verificar con una prueba por regla, incluida la de 450 m de diferencia de elevación
- [x] 3.2 Reunir `sources` a partir de los `source_id` usados; verificar con una prueba que recorre el cuerpo y comprueba que toda referencia está resuelta y no sobran fuentes
- [x] 3.3 Añadir una prueba que recorre todos los textos del perfil en ambos idiomas y falla ante expresiones de parcela ("tu parcela tiene", "your field has"); verificar que pasa

## 4. Endpoint

- [x] 4.1 Implementar `app/profile/builder.py` y conectar `GET /fields/{id}/profile` (geocerca del cliente → celda → perfil), con caché en memoria por celda, versión de datos e idioma; verificar con pruebas de `200`, `404` y de que la respuesta valida contra `FieldProfile`
- [x] 4.2 Medir la respuesta con datos sintéticos y verificar que tarda menos de 200 ms en la segunda llamada; regenerar `contracts/openapi.json` si cambió el modelo
- [x] 4.3 Añadir a `docs/api-contract.md` la tabla de códigos de `gaps` y la regla de la probabilidad mensual; verificar que cada código de la tabla existe en `gaps.py`
