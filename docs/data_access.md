# Acceso a los datos — guía para el backend

La API lee **solo** las vistas `v_*` de Athena. El contrato de columnas está en `docs/data_contract.md`.

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

DATA publica una política IAM administrada de solo lectura. Basta adjuntarla al rol de la tarea de la API:

```hcl
resource "aws_iam_role_policy_attachment" "api_gold_read" {
  role       = aws_iam_role.api.name
  policy_arn = "arn:aws:iam::<ACCOUNT_ID>:policy/fieldshift-gold-read"
}
```

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
`/fieldshift/data_version`. La API detecta el cambio leyendo ese parámetro. Publicaciones previstas:
integración de SMAP (humedad) y de NDVI (suelo descubierto); no cambian nombres de columnas.

## Sin AWS

`docs/data_sample/` trae una muestra real de las siete vistas para dos celdas, con las mismas columnas y
tipos que devuelve Athena, para pruebas locales y para el proveedor `fixture`.
