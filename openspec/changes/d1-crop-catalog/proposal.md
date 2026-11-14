# Proposal

## Why

Los motores de aptitud y de rotaciones comparan el clima y el suelo de la zona con lo que cada cultivo necesita y aporta. Esos requisitos tienen que estar en un catálogo único, revisable por el rol científico (SCI) sin tocar código, y con un esquema fijo desde el principio para que motores y SCI trabajen a la vez.

## What Changes

- Catálogo de cultivos en un archivo versionado (`data/crops.yaml`), validado al arrancar.
- `GET /api/v1/crops` real, con nombres en español e inglés.
- Cada cultivo lleva los campos que usan los motores: familia botánica, roles, ciclo, temperaturas, tolerancia a helada, temperatura crítica de calor, necesidad de agua, pH, coeficientes Kc, balance de nitrógeno, aporte de residuo y, si SCI lo entrega, índice relativo de margen.
- Arranca con 5 cultivos de ejemplo y se completa con los 12-15 que entregue SCI.

## Capabilities

### New Capabilities
- `crop-catalog`: catálogo de cultivos con los requisitos y aportes agronómicos que usan los motores y muestra el frontend.

### Modified Capabilities

Ninguna.

## Impact

- Nuevos: `data/crops.yaml`, `app/catalog/` (`models.py`, `loader.py`), `tests/catalog/`.
- `app/api/routes/crops.py` deja de devolver la respuesta fija.
- El esquema del catálogo queda congelado para `d2`, `d3` y `e2`; añadir campos es compatible, renombrarlos no.
- Tarea del plan: **D1** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 4 (Motores).
- Depende de: catálogo de SCI (P5 del plan); puede empezar con ejemplos.
- Estimación: 1 h.
