# Tasks

## 1. Carga

- [x] 1.1 Añadir `awswrangler` a las dependencias de ejecución y regenerar el bloqueo; verificar que la imagen construye, arranca y que `pip check` no informa conflictos
  - Decisión: se usa boto3 (ya era dependencia) en lugar de `awswrangler`, que añadiría pandas y pyarrow a la imagen sin aportar nada a seis `SELECT`. No hay dependencia nueva ni bloqueo que regenerar
- [x] 1.2 Implementar en `app/data/athena.py` un ejecutor de consultas (región, workgroup y base desde configuración, sin reutilización de resultados) detrás de una interfaz sustituible; verificar con una prueba que el ejecutor simulado recibe solo `SELECT` sobre vistas `v_*`
- [x] 1.3 Implementar la construcción de la instantánea: seis vistas a filas tipadas de `app/data/models.py`, `NaN` y rellenos a nulo, índices por `cell_id`; verificar con datos simulados que la prueba de conformidad de `c1` pasa para `AthenaProvider`
- [x] 1.4 Implementar la validación por vista (columnas obligatorias, al menos una celda, 36 decenas por celda en `v_cell_profile`); verificar con pruebas de columna ausente, columna extra y vista vacía

  - Cambio respecto al diseño: el contrato v2 de DATA (2,992 celdas, más de un millón de filas en `v_cell_indicators`) pide filtrar siempre por `cell_id`. Solo `v_cells` y `v_sources` se cargan completas; el resto se lee por celda en la primera petición y queda en memoria por versión y celda

## 2. Ciclo de vida

- [x] 2.1 Lanzar la carga inicial en segundo plano al arrancar la aplicación y reflejar el estado en `is_ready`; verificar con una prueba que `/health` responde antes de terminar la carga y `/ready` pasa de `503` a `200`
- [x] 2.2 Implementar el bucle que lee el parámetro SSM cada 5 minutos (intervalo configurable) y recarga solo si cambia, con intercambio atómico de la instantánea; verificar con una prueba de versión cambiada y otra de versión igual sin consultas
- [x] 2.3 Implementar la conservación de la última copia buena y el error `data_unavailable` cuando no hay ninguna; verificar con pruebas de recarga fallida y de carga inicial fallida
- [x] 2.4 Registrar en cada carga la versión, el número de celdas, la duración y, si falla, la vista y la causa; verificar en los registros de un arranque local con el ejecutor simulado

## 3. Activación

- [x] 3.1 Registrar `athena` en la fábrica de proveedores con sus variables de entorno; verificar con una prueba de configuración incompleta que el arranque falla indicando la variable que falta
- [x] 3.2 En un preview, con gold V0 publicado, desplegar con `DATA_PROVIDER=athena`; verificar que `/ready` informa la versión del parámetro SSM y que `GET /api/v1/sources` devuelve las fuentes reales
  - Verificado en el preview `pr-19` (15 de noviembre de 2026): `/ready` informa `2026111508`, `/sources` devuelve las fuentes reales y `scripts/smoke_e2e.py --require-real` termina con `OK` en las dos zonas
- [x] 3.3 Cambiar la variable de repositorio para `dev`, redesplegar y documentar en `README.md` el procedimiento de activación y de vuelta atrás; verificar que el perfil de una geocerca de cada zona responde `200`
  - Variable `DATA_PROVIDER=athena` y despliegue de `dev` tras fusionar el PR #19: `/ready` informa `2026111508` y `scripts/smoke_e2e.py --require-real` termina con `OK` en las dos zonas. Procedimiento de activación y vuelta atrás en `README.md`
  - Bloqueada por 3.2 y 4.1. El procedimiento de activación y de vuelta atrás ya está en `README.md`

## 4. Condiciones de integración (previas a la activación de la sección 3)

- [x] 4.1 Acordar con DATA, documentar e implementar en ambos proyectos un protocolo de publicación consistente; verificar con una publicación entre consultas que no se acepta una instantánea mezclada. Comprobar SSM antes y después no basta. Mantener `fixture` hasta satisfacer esta condición
  - Protocolo «versión en cada fila» (`docs/data_access.md`): las 8 vistas se recrearon con la columna `data_version` y la API rechaza cualquier fila de otra versión. Pendiente de DATA: llevar la columna a sus plantillas de `gold_build`
- [x] 4.2 Fijar `ctas_approach=False`, `unload_approach=False`, sin reutilización ni OutputLocation propio; verificar workgroup y región y ausencia de CTAS, UNLOAD y escrituras al catálogo
- [x] 4.3 Tratar SSM `none` como ausencia de publicación; probar arranque sin vistas, publicación posterior y conservación de una instantánea previa
- [x] 4.4 Confirmar que DATA aplicó su stack y ejecutó su pipeline con sus artefactos; verificar vistas y versión publicada sin aplicar `infra/data/` desde el backend
  - Verificado el 15 de noviembre de 2026: existen las vistas `v_*` y el parámetro vale `2026111508`. (Una nota anterior decía que faltaban: era un error de la terminal, que convertía la ruta del parámetro.)
- [x] 4.5 Verificar desde el rol real de la tarea lectura de SSM y SELECT en Athena en `DATA_REGION`, con política del rol y boundary compatibles, antes de 3.2 y 3.3
  - Verificado con el simulador de IAM sobre `nasa-farm-dev-api`: lectura de SSM, Athena, Glue, `gold/` y resultados permitidos con su límite de permisos
