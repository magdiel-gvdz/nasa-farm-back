# Tasks

## 1. Script

- [x] 1.1 Crear `scripts/smoke_e2e.py` (solo biblioteca estándar y `httpx`) con argumentos `--base-url`, `--zone` (`sureste` o `laguna`) y `--require-real`, que genera un `X-Client-Id` nuevo; verificar con `--help`
- [x] 1.2 Implementar el recorrido: `/health`, `/ready`, `/crops`, `/sources`, alta de una geocerca de la zona con rotación maíz-barbecho, perfil, aptitud en detalle y matriz, rotaciones y borrado en un bloque final que se ejecuta siempre; verificar contra la API local con datos sintéticos que termina con código 0
- [x] 1.3 Validar cada respuesta contra el esquema de `contracts/openapi.json` y aplicar comprobaciones de sentido: 36 decenas, al menos tres estrategias con una actual, toda `evidence` con `source_id` presente en `sources`; verificar introduciendo a mano una respuesta inválida en una prueba unitaria del validador
- [x] 1.4 Informar por paso de duración, estado y si la respuesta llevaba `X-Fieldshift-Mock`; con `--require-real`, fallar si algún paso del MVP sigue siendo respuesta fija; verificar ambos modos contra un preview
- [x] 1.5 Añadir un paso de escenario (`delta_t_c=2`) y otro de fuera de región (espera `out_of_region`) que se omiten con aviso si el endpoint aún responde con respuesta fija; verificar contra un preview

## 2. Uso

- [ ] 2.1 Añadir el script como paso posterior a la prueba de humo en `infrastructure.yml`, sin `--require-real`; verificar con `actionlint` y en la ejecución de un PR
- [x] 2.2 Escribir `docs/smoke.md` con los comandos para preview y `dev` y la lista de comprobación tras cada publicación de DATA (versión en `/ready`, script con `--require-real` en ambas zonas); verificar que los comandos funcionan tal como están escritos
