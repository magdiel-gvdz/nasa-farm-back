# Tasks

## 1. Imagen

- [x] 1.1 Crear `Dockerfile` con base `python:3.13-slim`, instalación desde `requirements.txt`, usuario sin root, `EXPOSE 8080` y arranque `uvicorn app.main:app --host 0.0.0.0 --port 8080`; verificar con `docker build -t fieldshift-api .`
- [x] 1.2 Crear `.dockerignore` que excluya `.git`, `.venv`, `.tools`, `infra`, `tests`, `docs`, `openspec`, `build` y `.env*`; verificar con `docker run --rm fieldshift-api ls -a /app` que no aparecen
- [x] 1.3 Mover `uvicorn` a dependencias de ejecución en `pyproject.toml` y regenerar el bloqueo de `requirements.txt` con sus transitivas; verificar que `pip install -r requirements.txt` en un entorno limpio permite `python -m uvicorn --version`
- [x] 1.4 Arrancar el contenedor con `ENVIRONMENT=pr-7` y verificar que `curl localhost:8080/health` devuelve `environment: pr-7` y que `docker exec <id> id -u` no es 0
- [x] 1.5 Verificar el apagado: `docker stop` termina en menos de 10 s con código de salida 0

## 2. CI

- [x] 2.1 Agregar a `.github/workflows/check.yml` un paso que construya la imagen, la arranque y consulte `/health`, sin quitar el paso del paquete Lambda; verificar con `actionlint` y con la ejecución del workflow en el PR
- [x] 2.2 Documentar en `README.md` (sección de desarrollo local) los comandos de construcción y arranque de la imagen; verificar que los comandos documentados funcionan tal como están escritos
