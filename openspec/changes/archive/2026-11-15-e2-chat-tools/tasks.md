# Tasks

## 1. Registro y herramientas

- [x] 1.1 Crear `app/agent/tools/registry.py` con la definición de herramienta (nombre, descripción, esquema de entrada estricto, función, etiqueta es/en, tipo de tarjeta opcional) y el contexto de ejecución con el `client_id` de la conversación; verificar con una prueba que el esquema exportado al modelo es válido
- [x] 1.2 Implementar `list_user_fields`, `get_field_profile` (con selección de secciones) y `get_risk_calendar` (rango de decenas) sobre `app/store` y `app/profile`; verificar con pruebas de resultado y de geocerca ajena
- [x] 1.3 Implementar `evaluate_crop`, `suitability_matrix`, `compare_rotations` y `list_crops` sobre los motores y el catálogo, aceptando escenario opcional si existe `d4`; verificar con una prueba de igualdad entre la herramienta y el endpoint
- [x] 1.4 Recortar los resultados grandes antes de entregarlos al modelo (por ejemplo, matriz sin textos largos) conservando valores y `source_id`; verificar con una prueba de tamaño máximo por resultado

## 2. Bucle en el flujo

- [x] 2.1 Extender `app/agent/stream.py` para ejecutar las herramientas que pide el modelo y devolverle los resultados, con un máximo de 8 invocaciones por mensaje; verificar con el cliente simulado en secuencias de una y de varias herramientas y del tope
- [x] 2.2 Emitir eventos `tool` (`running`, `done`, `failed`) con etiqueta en el idioma de la petición y convertir errores de herramienta en resultados de error para el modelo; verificar con la prueba del cultivo inexistente
- [x] 2.3 Emitir `card` para aptitud y rotaciones y `citation` sin repetir a partir de los `source_id` de los resultados; verificar con pruebas de ambos eventos

## 3. Verificación

- [x] 3.1 En un preview, preguntar "¿puedo sembrar maíz en abril?" con una geocerca activa y verificar con `curl -N` la secuencia `tool` → `card` → `text` → `citation` → `done`
  - Preview `pr-20`: "¿Puedo sembrar maíz en abril?" → `status` → `text` → `tool` (running, done) → `card` (`suitability`) → `text` → `citation` ×2 → `done`, con la cifra de la herramienta (42/100) y su fuente
- [x] 3.2 Documentar en `docs/api-contract.md` la lista de herramientas, los tipos de `card` y sus esquemas; verificar que cada tipo documentado tiene una prueba
