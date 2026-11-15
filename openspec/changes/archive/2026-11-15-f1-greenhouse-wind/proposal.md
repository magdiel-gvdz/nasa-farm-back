# Proposal

## Why

El agrónomo que asesora al equipo señaló que en invernaderos lo primero es saber qué viento puede dañar la estructura. Con la serie diaria de viento máximo se puede estimar el viento esperable cada 10, 25 y 50 años y compararlo con la resistencia que declara el fabricante. Es la segunda extensión: solo se aborda con el MVP estable.

## What Changes

- `GET /api/v1/fields/{id}/greenhouse` para geocercas de tipo invernadero.
- Ajuste estadístico de extremos (Gumbel) sobre el viento máximo anual, niveles de retorno y probabilidad anual de superar la resistencia declarada.
- Meses de mayor riesgo y recomendaciones por plantillas.
- Declaración explícita de que el dato es viento medio horario máximo a escala de ~55 km, no ráfaga local.
- Fuera de alcance: luz, calefacción, CO₂ y granizo del handoff §6.6; se devuelven como `null` con su vacío declarado.

## Capabilities

### New Capabilities
- `greenhouse-wind`: estimación del riesgo de viento para la estructura de un invernadero.

### Modified Capabilities

Ninguna.

## Impact

- Nuevos: `app/engines/greenhouse.py`, `app/api/routes/greenhouse.py`, `tests/engines/test_greenhouse.py`.
- Necesita una serie diaria larga; con solo 2016-2025 el resultado se marca como poco fiable.
- Tarea del plan: **F1** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 3 (Datos y perfil).
- Depende de: `c4-daily-series`, `b3-fields-store`.
- Estimación: 2.5 h.
