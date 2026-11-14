# Proposal

## Why

Es el resultado central del reto: comparar al menos tres estrategias de rotación, incluida la actual del agricultor, y explicar para cada una por qué se sugiere, qué evidencia la respalda, qué beneficios puede dar, dónde faltan datos y qué riesgos debe revisar un agrónomo local. Sin este endpoint no hay producto que presentar.

## What Changes

- `POST /api/v1/fields/{id}/rotations` real.
- Genera estrategias a partir de la rotación actual y de plantillas (leguminosa, cobertura en la ventana de suelo descubierto, cultivo tolerante a sequía, forraje si hay ganado), filtradas por aptitud y por las restricciones del agricultor.
- Simula cada estrategia a varios años y calcula métricas de agua, nitrógeno, materia orgánica, suelo descubierto, exposición a erosión y ruptura de plagas.
- Puntúa según las prioridades del agricultor y devuelve textos explicativos generados con plantillas a partir de las métricas.

## Capabilities

### New Capabilities
- `rotation-strategies`: generación, simulación, puntuación y explicación de estrategias de rotación de cultivos para una geocerca.

### Modified Capabilities

Ninguna.

## Impact

- Nuevos: `app/engines/rotation/` (`candidates.py`, `simulate.py`, `score.py`, `explain.py`), plantillas de texto es/en, `tests/engines/rotation/`.
- `app/api/routes/rotations.py` deja de devolver la respuesta fija.
- Es la tarea más larga del plan (5 h). Si en H20 no hay tres estrategias, se reducen plantillas y métricas, nunca los textos explicativos.
- Tarea del plan: **D3** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 4 (Motores).
- Depende de: `d2-crop-suitability` (basta su firma para empezar), `d1-crop-catalog`, `c1-data-provider`.
- Estimación: 5 h.
