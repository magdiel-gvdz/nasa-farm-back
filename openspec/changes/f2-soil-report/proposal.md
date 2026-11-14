# Proposal

## Why

El suelo de SoilGrids es una estimación a 250 m promediada a 9 km, y no existe fuente global de fósforo, potasio ni micronutrientes: el propio perfil lo declara como vacío. El agrónomo insistió en que lo más importante es conocer la materia orgánica y los nutrientes reales. Si el agricultor ya tiene un análisis de laboratorio, subirlo sustituye la estimación por una medición de su parcela.

## What Changes

- `POST /api/v1/fields/{id}/soil-report` acepta un PDF o una foto del análisis.
- Un modelo de lenguaje extrae los valores a una estructura fija; los valores fuera de rangos plausibles se descartan.
- Los valores aceptados se guardan en la geocerca y aparecen en `soil.lab` del perfil; la confianza del suelo pasa a alta y desaparece el vacío de análisis de laboratorio.
- El motor de aptitud usa el pH de laboratorio cuando existe.

## Capabilities

### New Capabilities
- `soil-report`: incorporación del análisis de suelo de laboratorio del agricultor al perfil de su geocerca.

### Modified Capabilities

Ninguna.

## Impact

- Nuevos: `app/agent/extract.py`, `app/api/routes/soil_report.py`, `tests/agent/test_extract.py`.
- Cambios menores en `app/profile` y en el factor suelo de `app/engines/suitability.py`.
- Archivos en `uploads/` del bucket del entorno. Requiere el chat activo (mismo acceso al modelo).
- Tarea del plan: **F2** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 1 (Plataforma).
- Depende de: `e1-chat-streaming`, `c3-field-profile`.
- Estimación: 3 h.
