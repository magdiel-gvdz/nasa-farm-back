# Tasks

## 1. Base del motor

- [ ] 1.1 Publicar en `app/engines/suitability.py` la firma `evaluate(crop, planting_month, cell_data, field_context, scenario=None)` y los tipos de resultado, con una implementación mínima, y avisar a quien lleve `d3`; verificar con una prueba que importa y llama a la función
- [ ] 1.2 Crear `config/engine.yaml` con cortes de estado, pesos por factor, umbrales de probabilidad para `warn` y `bad`, fracción de lluvia efectiva (0.8) y ventana de floración (55-65 % del ciclo), cargado y validado al arrancar; verificar con una prueba de carga y otra de valor fuera de rango
- [ ] 1.3 Implementar la conversión de mes de siembra y días de ciclo a decenas ocupadas, cruzando el fin de año, y la ventana de cosecha; verificar con pruebas de un ciclo de 120 días desde abril y de uno que cruza diciembre

## 2. Factores

- [ ] 2.1 Implementar el factor helada sobre `frost_prob` de las decenas del ciclo, con la excepción de cultivos tolerantes; verificar con datos sintéticos de Saltillo que maíz en enero es `bad` y avena en noviembre no
- [ ] 2.2 Implementar el factor calor con el umbral `hot_prob_*` más cercano a `heat_critical_c` en la ventana de floración; verificar con la prueba del umbral de 35 °C y con datos de La Laguna
- [ ] 2.3 Implementar en `app/engines/water.py` la demanda (Kc por etapa × `et0_p50` por decena), la lluvia efectiva y el déficit con el riego de la geocerca; verificar con la prueba de 620, 240 y 200 mm y con el caso sin riego declarado
- [ ] 2.4 Implementar el factor suelo (pH de 0-5 cm y textura); verificar con pH 8.4 frente a rango 5.5-7.5
- [ ] 2.5 Implementar textos de `detail` es/en con plantillas que incluyen los valores y el umbral usado, y el `source_id` de cada factor; verificar con una prueba que comprueba valores y fuente en el texto

## 3. Puntaje y endpoint

- [ ] 3.1 Implementar la combinación ponderada, los factores excluyentes, el estado, la confianza y el tratamiento de factores `unknown`; verificar con pruebas de los tres estados y del caso sin suelo
- [ ] 3.2 Conectar el modo detalle y el modo matriz en `GET /fields/{id}/suitability`, con errores `crop_not_found` y de validación, y quitar la respuesta fija; verificar con pruebas de API y de coherencia entre matriz y detalle
- [ ] 3.3 Medir la matriz completa con el catálogo de 15 cultivos y verificar que tarda menos de 300 ms; añadir caché por celda, versión de datos, riego e idioma si no se cumple
- [ ] 3.4 Documentar en `docs/engines.md` cada factor, su fórmula, sus umbrales y su fuente, para la revisión de SCI; verificar que cada parámetro de `config/engine.yaml` aparece en el documento
