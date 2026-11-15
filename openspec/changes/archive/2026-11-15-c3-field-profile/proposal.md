# Proposal

## Why

El perfil agroclimático es lo primero que ve el agricultor tras marcar su terreno y es la fuente de la que leen el frontend y el chat. Gold entrega indicadores por decena con nombres pensados para el pipeline; hay que convertirlos en el perfil del contrato, con cada cifra trazada a su fuente y con los límites del dato dichos con claridad, que es además lo que el reto evalúa.

## What Changes

- `GET /api/v1/fields/{id}/profile` real: sustituye la respuesta fija.
- Clima por mes (heladas, lluvia, calor, viento) y calendario de riesgos de 36 decenas con las decenas vulnerables y sus motivos.
- Suelo por profundidad con rango P05-P95, humedad del suelo, balance hídrico y vegetación.
- Lista de fuentes usadas y lista de vacíos de información generada por reglas.
- Todos los textos hablan de "tu zona (celda de 9 km)", nunca de la parcela.

## Capabilities

### New Capabilities
- `field-profile`: perfil agroclimático histórico de la zona de una geocerca, con procedencia y vacíos de información.

### Modified Capabilities

Ninguna.

## Impact

- Nuevos: `app/profile/` (`builder.py`, `gaps.py`, `monthly.py`), `tests/profile/`.
- `app/api/routes/profile.py` deja de devolver la respuesta fija.
- Lo consumen las herramientas del chat (`e2-chat-tools`).
- Tarea del plan: **C3** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 3 (Datos y perfil).
- Depende de: `c1-data-provider`, `b1-api-contract`.
- Estimación: 3 h.
