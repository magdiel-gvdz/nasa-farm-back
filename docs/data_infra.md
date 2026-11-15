# Infraestructura de datos — pila `fieldshift-data`

Infraestructura que produce y publica los datos que consume la API. La despliega y mantiene DATA con
Terraform, **desde el proyecto de datos**, con su propio estado. `infra/data/` en este repositorio es una
copia de referencia: no se aplica desde aquí ni desde el CI.

```
 NASA POWER ──► Lambda ingest-power ─────┐
 SoilGrids WCS ► Lambda ingest-soil ─────┤
 Copernicus DEM ► Lambda ingest-elevation┼─► S3 lake raw/ ─► Glue silver-build ─► silver/ ─► Glue gold-build ─► gold/
 AppEEARS (SMAP, NDVI) ► Lambda          │                                                        │
        appeears-poll (cada 15 min) ─────┘                                  vistas v_* de Athena + SSM data_version
                                                                                                  │
                                                                              API (us-east-1) lee con fieldshift-gold-read
```

Región: **us-west-2**. Cuenta: la misma que la API.

| Recurso | Nombre | Uso |
|---|---|---|
| S3 | `fieldshift-lake-<ACCOUNT_ID>` | `raw/`, `silver/`, `gold/`, `code/`. Privado, cifrado, versionado |
| S3 | `fieldshift-athena-results-<ACCOUNT_ID>` | Resultados de Athena (se borran a los 7 días) |
| Glue Data Catalog | `fieldshift_silver`, `fieldshift_gold` | Tablas y vistas |
| Athena | workgroup `fieldshift` | Límite de 1 GB escaneado por consulta |
| SSM | `/fieldshift/data_version` | Versión vigente de gold |
| Secrets Manager | `fieldshift/earthdata` | Credenciales Earthdata para AppEEARS (valor cargado fuera de Terraform) |
| ECR | `fieldshift-ingest` | Imagen única (arm64) de las Lambdas de ingesta |
| Lambda | `fieldshift-ingest-power`, `-ingest-soil`, `-ingest-elevation`, `fieldshift-appeears-poll` | Extracción a `raw/` |
| EventBridge | `fieldshift-appeears-poll` | Cada 15 min mientras haya tareas de AppEEARS pendientes |
| Glue (Python shell 3.9) | `fieldshift-silver-build`, `fieldshift-gold-build` | Transformación y publicación |
| IAM | `fieldshift-ingest-lambda`, `fieldshift-glue` | Roles de mínimo privilegio |
| IAM | política `fieldshift-gold-read` | Solo lectura para la API |

Capas del lake:
- **raw:** respuesta de cada fuente tal cual, con su petición. Solo escriben las Lambdas.
- **silver:** una tabla por fuente, unidades limpias, sin rellenos, UTC, por celda.
- **gold:** indicadores por celda, año y decena; climatología; suelo; serie diaria. Partición `data_version`.

Costo esperado: menos de 5 USD en el hackathon (sin VPC ni NAT, Glue Python shell de 0.0625 DPU, logs de 7 días).
