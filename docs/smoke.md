# Prueba de humo de extremo a extremo

`scripts/smoke_e2e.py` recorre contra una URL lo que hace un usuario: catálogo, fuentes, alta de
una geocerca, perfil, aptitud (matriz y detalle), rotaciones, un escenario de +2 °C, un alta fuera
de región y el borrado. Valida cada respuesta contra `contracts/openapi.json` y comprueba que el
calendario trae 36 decenas, que hay al menos tres estrategias con una actual y que toda evidencia
cita una fuente de `/sources`.

Cada ejecución usa un `X-Client-Id` nuevo y borra su geocerca aunque falle un paso. Solo necesita
Python y `httpx` (ya está en `requirements-dev.txt`).

## Comandos

Contra un preview, antes de fusionar (la URL está en el resumen del job `deploy` del PR):

```powershell
.\.venv\Scripts\python.exe scripts/smoke_e2e.py --base-url https://<url-del-preview>
```

Contra `dev`, en las dos zonas con datos sintéticos:

```powershell
.\.venv\Scripts\python.exe scripts/smoke_e2e.py --base-url https://<url-de-dev> --zone sureste
.\.venv\Scripts\python.exe scripts/smoke_e2e.py --base-url https://<url-de-dev> --zone laguna
```

Contra la API local (`uvicorn app.main:app --port 8080`):

```powershell
.\.venv\Scripts\python.exe scripts/smoke_e2e.py --base-url http://localhost:8080
```

El workflow de despliegue lo ejecuta solo después de cada apply, sin `--require-real`.

## Cómo leer la salida

Una línea por paso con su estado (`ok`, `fail`, `skip`), la duración y si la respuesta fue `real`
o `fija` (llevaba `X-Fieldshift-Mock`). El código de salida es 0 si ningún paso falla.

- `skip` en `scenario` significa que la aptitud todavía es una respuesta fija y un escenario no
  diría nada.
- Con `--require-real` el script falla además si algún paso del MVP (`crops`, `sources`,
  `create_field`, `profile`, `suitability_matrix`, `suitability_detail`, `rotations`) sigue siendo
  una respuesta fija, y los nombra.
- Un fallo de esquema (`falta 'name'`, por ejemplo) contra `dev` justo después de fusionar suele
  indicar que `dev` aún sirve la imagen anterior: comprobar que el despliegue de `main` terminó.

## Tras cada publicación de DATA

1. `GET /ready` informa en `data_version` la versión que anunció DATA (no `fixture`).
2. `scripts/smoke_e2e.py --base-url <dev> --zone sureste --require-real` termina con `OK`.
3. Lo mismo con `--zone laguna`.

## Precaución con `dev`

`dev` despliega con una estrategia canario que revierte sola si sube la tasa de errores del
balanceador. No lanzar la prueba contra `dev` mientras hay un despliegue en curso: sus respuestas
`4xx` esperadas cuentan como errores.
