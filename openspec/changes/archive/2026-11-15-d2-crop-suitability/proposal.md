# Proposal

## Why

La pregunta más directa del agricultor es "¿puedo sembrar este cultivo en este mes?". Responderla con un semáforo razonado, citando la fuente de cada motivo, es la base del producto: el motor de rotaciones usa esta misma evaluación para descartar y puntuar cultivos.

## What Changes

- `GET /api/v1/fields/{id}/suitability` real, en dos modos: detalle de un cultivo y mes de siembra, y matriz de todos los cultivos por los 12 meses.
- Evaluación por cuatro factores (helada, calor, agua y suelo), cada uno con estado, explicación y fuente.
- Puntaje de 0 a 100 y estado `suitable`, `marginal` o `unsuitable`.
- Motor determinista, sin modelos estadísticos; umbrales y pesos en configuración.

## Capabilities

### New Capabilities
- `crop-suitability`: evaluación explicada de si un cultivo puede sembrarse en un mes dado en la zona de una geocerca.

### Modified Capabilities

Ninguna.

## Impact

- Nuevos: `app/engines/suitability.py`, `app/engines/water.py`, `config/engine.yaml`, `tests/engines/`.
- `app/api/routes/suitability.py` deja de devolver la respuesta fija.
- La firma de la función de evaluación se publica en el primer commit del PR para que `d3-rotation-strategies` empiece en paralelo.
- Tarea del plan: **D2** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 4 (Motores).
- Depende de: `c1-data-provider`, `d1-crop-catalog`.
- Estimación: 3 h.
