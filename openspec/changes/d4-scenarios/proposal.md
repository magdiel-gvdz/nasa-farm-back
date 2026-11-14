# Proposal

## Why

El reto pide controles de escenario para explorar qué pasa si cambia la temperatura o la lluvia. Con indicadores ya agregados no se puede responder: hay que aplicar el cambio a la serie diaria y volver a contar heladas, días de calor y balance hídrico, y hacerlo lo bastante rápido para que el control se sienta inmediato.

## What Changes

- Parámetros de escenario `delta_t_c` y `delta_p_pct` en aptitud y en rotaciones.
- Con un escenario distinto de cero, los indicadores de la celda se recalculan desde la serie diaria modificada y los motores usan esos indicadores.
- Las respuestas indican el escenario aplicado y de dónde salió la serie diaria.
- Con escenario cero, el resultado es el de siempre (indicadores de gold).

## Capabilities

### New Capabilities
- `scenarios`: evaluación de aptitud y rotaciones bajo cambios hipotéticos de temperatura y lluvia.

### Modified Capabilities

Ninguna.

## Impact

- Nuevos: `app/engines/scenario.py`, `app/engines/indicators.py` (o el módulo de indicadores de DATA incorporado), `tests/engines/test_scenario.py`.
- `d2` y `d3` reciben los indicadores por parámetro; no cambian sus reglas.
- Depende de que exista serie diaria (`c4-daily-series`).
- Tarea del plan: **D4** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 4 (Motores).
- Depende de: `c4-daily-series`, `d2-crop-suitability`; módulo de indicadores de DATA (P6 del plan).
- Estimación: 3 h.
