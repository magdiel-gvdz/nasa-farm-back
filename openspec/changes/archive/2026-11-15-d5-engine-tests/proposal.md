# Proposal

## Why

Los motores deciden lo que la herramienta recomienda al agricultor y se van a retocar hasta el último momento (umbrales de SCI, textos, pesos). Cada cambio tardío puede romper una regla sin que nadie lo note. Una batería de casos agronómicos con resultado conocido, ejecutada en CI, protege la demo.

## What Changes

- Casos de regresión de punta a punta sobre los motores, con datos sintéticos diseñados para tener una respuesta evidente.
- Instantáneas de las respuestas de las dos geocercas de demostración para detectar cambios no intencionados.
- Sin cambios de comportamiento: este cambio no lleva especificaciones (`skip_specs`); verifica las de `crop-suitability`, `rotation-strategies` y `scenarios`.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

Ninguna.

## Impact

- Nuevos: `tests/engines/test_agronomy_cases.py`, `tests/engines/snapshots/`, generadores de celdas sintéticas en `tests/engines/builders.py`.
- Sin cambios en código de aplicación, salvo defectos que las pruebas descubran.
- Tarea del plan: **D5** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 4 (Motores).
- Depende de: `d2-crop-suitability`, `d3-rotation-strategies`.
- Estimación: 1.5 h.
