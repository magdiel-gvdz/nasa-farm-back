# Proposal

## Why

La presentación dura pocos minutos y se hace sobre `dev`. Dibujar un polígono en directo y esperar que todo salga bien es un riesgo innecesario. Dos geocercas preparadas, con una historia agronómica clara y revisada por el rol científico, aseguran una demo que enseña lo que el reto pide: rotación actual frente a alternativas, periodos vulnerables, vacíos de información y escenarios.

## What Changes

- Dos geocercas de demostración con su rotación actual, riego y prioridades: un rancho en el Sureste (Saltillo: heladas, maíz-barbecho) y una parcela en La Laguna (calor extremo y agua limitada, forraje).
- Script que las crea en un entorno bajo un `X-Client-Id` fijo y documentado.
- Guion de la demo con las llamadas, los resultados esperados y las frases sobre límites de los datos.
- Revisión de resultados con SCI y corrección de lo que no sea defendible.
- Datos y guion de demostración, sin cambio de comportamiento de la API (`skip_specs`).

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

Ninguna.

## Impact

- Nuevos: `demo/fields.json`, `scripts/seed_demo.py`, `docs/demo-script.md`.
- Puede originar ajustes en `config/engine.yaml`, `data/crops.yaml` o en textos de rotaciones.
- Tarea del plan: **G2** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 4 (Motores).
- Depende de: `c2-athena-provider` con gold real, `d3-rotation-strategies`.
- Estimación: 1.5 h.
