# Tasks

## 1. Errores

- [x] 1.1 Crear `app/api/errors.py` con una excepción de aplicación (`code`, estado, `details`) y manejadores para ella, para errores de validación, para `404`/`405` del enrutador y para excepciones no controladas; verificar con pruebas de cada caso que el cuerpo cumple el sobre
- [x] 1.2 Sustituir el manejador de `DataUnavailableError` por el sobre común con `data_unavailable`; verificar con la prueba de `/ready`

## 2. Identidad e idioma

- [x] 2.1 Crear en `app/api/deps.py` la dependencia `client_id` (UUID obligatorio) y aplicarla a las rutas de `/fields`; verificar con pruebas de encabezado ausente, inválido y válido, y que `/crops` y `/sources` no lo exigen
- [x] 2.2 Crear `app/i18n.py` con resolución de idioma desde `Accept-Language` y un catálogo de mensajes es/en con claves; usarlo en los mensajes de error; verificar con pruebas de `en`, `es`, `fr` y encabezado ausente

## 3. CORS y disponibilidad

- [x] 3.1 Actualizar el middleware CORS en `app/main.py` (métodos, encabezados permitidos y expuestos); verificar con pruebas de preflight para `PATCH` y `DELETE` y de origen desconocido
- [x] 3.2 Reescribir `/ready` para consultar el estado del proveedor de datos mediante una interfaz mínima (`is_ready`, `data_version`), con una implementación provisional siempre lista hasta que llegue `c1-data-provider`; verificar con pruebas de listo y no listo
- [x] 3.3 Añadir a `docs/api-contract.md` la tabla de códigos de error y los encabezados; verificar que cada código de la tabla aparece en al menos una prueba
