# Proposal

## Why

El contrato fija la forma de las respuestas correctas, pero faltan las reglas comunes a todos los endpoints: cómo se informa un error, cómo se identifica al cliente sin inicio de sesión, en qué idioma se responden los textos y qué permite CORS. Hoy CORS solo admite `GET` y `POST` y no deja pasar el encabezado `X-Client-Id`, así que el frontend no podría editar ni borrar geocercas.

## What Changes

- Sobre de error único: `{"error": {"code", "message", "details"}}` para todo error, incluidos los de validación.
- Identidad por encabezado `X-Client-Id` (UUID generado por el frontend) obligatoria en los endpoints con datos del usuario.
- Idioma de los textos según `Accept-Language` (`es` por defecto, `en` admitido).
- CORS admite `GET`, `POST`, `PATCH`, `DELETE`, `OPTIONS` y los encabezados `Content-Type`, `X-Client-Id` y `Accept-Language`, y expone `X-Fieldshift-Mock`.
- **BREAKING**: `/ready` deja de leer el manifiesto de S3 e informa del estado del proveedor de datos; el error `{"detail": "DATA_UNAVAILABLE"}` pasa al sobre común.

## Capabilities

### New Capabilities
- `api-conventions`: reglas transversales de la API (errores, identidad del cliente, idioma, CORS y disponibilidad).

### Modified Capabilities

Ninguna.

## Impact

- `app/main.py`, nuevos `app/api/errors.py`, `app/api/deps.py`, `app/i18n.py`; pruebas en `tests/api/`.
- El chat (`e1`) y el límite de uso (`e5`) reutilizan la dependencia de identidad.
- Tarea del plan: **B2** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 2 (API y estado).
- Depende de: `b1-api-contract`.
- Estimación: 1 h.
