# Proposal

## Why

Gold solo contiene indicadores ya agregados por decena. Los escenarios ("¿y si sube 2 °C?") y el análisis de viento extremo para invernaderos necesitan la serie diaria, para aplicar el cambio y volver a contar eventos. DATA puede publicarla como una vista adicional, pero no está garantizado; hace falta un respaldo que no dependa de eso.

## What Changes

- Acceso a la serie diaria por celda a través del proveedor de datos.
- Origen preferente: vista `v_cell_daily` de DATA, si existe.
- Respaldo: NASA POWER en vivo, una llamada por cuadro de 0.5°, con caché en el bucket del entorno y la misma corrección de temperatura por altura que usa DATA.
- La respuesta indica de dónde salió la serie. Si ninguna vía funciona, solo fallan las funciones que la necesitan.

## Capabilities

### New Capabilities
- `daily-series`: serie meteorológica diaria por celda para cálculos que no pueden hacerse con indicadores agregados.

### Modified Capabilities

Ninguna.

## Impact

- Nuevos: `app/data/daily.py`, `app/data/power.py`, `tests/data/test_daily.py`.
- Usa `cache/power/` del bucket del entorno (`APP_BUCKET`); en local, un directorio temporal.
- Salida a Internet hacia `power.larc.nasa.gov` desde el contenedor.
- Lo consumen `d4-scenarios` y `f1-greenhouse-wind`.
- Tarea del plan: **C4** en `docs/plan-backend.md`.
- Responsable sugerido: Carril 3 (Datos y perfil).
- Depende de: `c1-data-provider`; respuesta de DATA sobre `v_cell_daily` (P3 del plan).
- Estimación: 2 h.
