# Acceso a los datos — guía para el backend

El proveedor Athena de la API deberá leer **solo** las vistas `v_*`. El contrato de columnas está en
`docs/data_contract.md`.

Esta entrega documenta los datos publicados; no implementa todavía el proveedor Athena ni configura
su acceso en la Lambda. La API actual sigue leyendo el manifiesto de su bucket S3. Las variables y el
ejemplo de permisos de esta guía son requisitos para esa integración posterior.

## Variables de entorno

| Variable | Valor |
|---|---|
| `DATA_PROVIDER` | `athena` |
| `DATA_REGION` | `us-west-2` |
| `ATHENA_WORKGROUP` | `fieldshift` |
| `ATHENA_DATABASE` | `fieldshift_gold` |
| `DATA_VERSION_PARAMETER` | `/fieldshift/data_version` |

La API vive en us-east-1 y los datos en us-west-2, en la misma cuenta: los clientes de Athena, Glue, S3 y SSM
deben crearse con `region_name = DATA_REGION`.

## Permisos

DATA publica una política IAM administrada de solo lectura. La integración debe adjuntarla al rol de
ejecución de la Lambda de la API:

```hcl
resource "aws_iam_role_policy_attachment" "api_gold_read" {
  role       = aws_iam_role.api.name
  policy_arn = "arn:aws:iam::<ACCOUNT_ID>:policy/fieldshift-gold-read"
}
```

Además, el rol de la API tiene una **permissions boundary** (`nasa-farm-runtime-boundary`) definida en
`infra/bootstrap/main.tf`. Actualmente solo permite logs y lecturas de `curated/` y `manifests/` del
bucket de la API. Adjuntar `fieldshift-gold-read` por sí solo no habilita Athena: el acceso efectivo es
la intersección entre las políticas del rol y su boundary.

Antes de habilitar el proveedor, se deben ampliar los permisos de la boundary para las acciones y
recursos de `fieldshift-gold-read` (Athena, Glue y SSM en `us-west-2`, lectura de `gold/` y lectura/escritura
de resultados), conservando los permisos existentes. Ese cambio requiere actualizar el bootstrap;
el despliegue de `infra/environment` no modifica la boundary. Después se adjunta la política al rol y se
configuran las variables de entorno de la Lambda. `infra/data/` es una referencia y no se aplica desde
el CI de este repositorio.

Qué permite: ejecutar consultas en el workgroup `fieldshift`, leer el catálogo de `fieldshift_gold`, leer
`s3://fieldshift-lake-<ACCOUNT_ID>/gold/*`, leer y escribir resultados en
`s3://fieldshift-athena-results-<ACCOUNT_ID>/`, y leer el parámetro SSM de la versión.
Qué no permite: escribir en el lake, leer `raw/` o `silver/`, cambiar tablas, vistas o el parámetro.

El workgroup fija la ubicación de resultados; no hay que pasar `OutputLocation`.

## Ejemplo mínimo (boto3)

```python
import boto3

session = boto3.Session(region_name="us-west-2")
version = session.client("ssm").get_parameter(Name="/fieldshift/data_version")["Parameter"]["Value"]
athena = session.client("athena")
qid = athena.start_query_execution(
    QueryString="SELECT * FROM v_cell_profile WHERE cell_id = ? ORDER BY decade",
    ExecutionParameters=["'E9_r0465_c0847'"],
    QueryExecutionContext={"Database": "fieldshift_gold"},
    WorkGroup="fieldshift",
)["QueryExecutionId"]
```

Con `awswrangler`: `wr.athena.read_sql_query(sql, database="fieldshift_gold", workgroup="fieldshift",
boto3_session=session, ctas_approach=False)`.

## Publicaciones

Cada publicación de DATA crea una partición nueva, recrea las vistas y actualiza
`/fieldshift/data_version`. El proveedor Athena deberá detectar el cambio leyendo ese parámetro. Publicaciones previstas:
integración de SMAP (humedad) y de NDVI (suelo descubierto); no cambian nombres de columnas.

## Sin AWS

`docs/data_sample/` trae una muestra real de las siete vistas para dos celdas, con las mismas columnas y
tipos que devuelve Athena, para pruebas locales y para el futuro proveedor `fixture`. Los valores
numéricos están redondeados a seis decimales; al comparar agregados de la muestra, usar una tolerancia
absoluta de `0.0001` para cantidades continuas. Los conteos enteros deben coincidir exactamente.
