# Verificación de la plataforma A

Verificado el 14 de noviembre de 2026 en la cuenta `028610956742`.
La API vive en `us-east-1`; DATA, en `us-west-2`.

## Acceso a DATA

Los outputs del estado `fieldshift-data/terraform.tfstate` confirman:

| Recurso | Valor |
| --- | --- |
| Lake compartido | `fieldshift-lake-028610956742` |
| Resultados | `fieldshift-athena-results-028610956742` |
| Workgroup | `fieldshift` |
| Base gold | `fieldshift_gold` |
| Versión | `/fieldshift/data_version` |

La política del rol y su boundary permiten SSM, Athena, catálogo gold, lectura
de `gold/` y resultados de Athena. La simulación IAM deniega escritura en el
lake, lectura de `raw/`, cambios del catálogo y actualización de SSM. Repetir
las simulaciones con una de las dos capas sin concesión deniega el acceso.

Una tarea Fargate temporal ejecutó la misma definición y el mismo rol
`nasa-farm-pr-7-api` que el servicio. Leyó `data_version=2026111501` y ejecutó
`SELECT count(*) AS cells FROM v_cells`: **136 celdas**.
Consulta Athena: `ff468bf2-7ef1-4d43-abb7-ddc645cac134`.
La tarea terminó correctamente y no queda ejecutándose.

## Preview y transición

`pr-7` responde `/health` y al preflight CORS de un origen externo con
`access-control-allow-origin: *`, por decisión explícita del usuario.
La URL se obtiene de `ingress_paths.endpoint` filtrando `access_type=PUBLIC`.
Express Mode está disponible: no aplica el respaldo Fargate + ALB manual.

El PR #6 (API b1-b4) se fusionó en `main` el 14 de noviembre y su preview
Lambda `pr-6` se destruyó al cerrarse. Esta rama incorpora ese código sobre el
contenedor: se retiran Mangum y el empaquetador de Lambda, y `pyproj`,
`shapely` y `numpy` quedan en el bloqueo de ejecución de la imagen.

El lector del manifiesto de S3, sus pruebas y
`contracts/data-manifest.schema.json` se eliminaron: `/ready` ya no consulta el
manifiesto y nada más los usaba. Las referencias a Lambdas de ingesta en
`infra/data` corresponden a DATA y siguen vigentes. Los permisos heredados de
Lambda y API Gateway del bootstrap se retiran en `a5-migrate-dev` 2.2, cuando
`dev` ya no los necesite.
