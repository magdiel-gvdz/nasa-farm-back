# Pila de datos `fieldshift-data` (copia de referencia)

Terraform de la infraestructura que produce los datos que lee la API: lake en S3, Glue, Athena, Lambdas
de ingesta, SSM y la política de solo lectura `fieldshift-gold-read`. Región `us-west-2`.

**Esta carpeta es una copia de referencia.** La pila se aplica desde el proyecto de datos, que es donde
viven el código de Glue (`glue/`), el paquete `build/fieldshift_glue.zip` y la imagen de las Lambdas que
este Terraform referencia. Desde este repositorio no se puede aplicar tal cual, y el CI no la despliega
(solo comprueba su formato con `terraform fmt`).

- Qué crea y cómo se conecta la API: [`docs/data_infra.md`](../../docs/data_infra.md) y
  [`docs/data_access.md`](../../docs/data_access.md).
- Contrato de las vistas: [`docs/data_contract.md`](../../docs/data_contract.md).
- Estado remoto: bucket propio de DATA (ver `backend.example.hcl`), separado del estado de la API.
- Dudas o cambios: ingeniería de datos.

| Archivo | Contenido |
|---|---|
| `s3.tf` | Buckets del lake y de resultados de Athena |
| `glue_athena.tf` | Bases `fieldshift_silver` y `fieldshift_gold`, workgroup `fieldshift` |
| `glue_jobs.tf` | Jobs `fieldshift-silver-build` y `fieldshift-gold-build` |
| `lambda.tf` | Lambdas de ingesta y horario de `appeears-poll` |
| `ssm_secrets_ecr.tf` | Parámetro de versión, secreto Earthdata (sin valor), ECR, logs |
| `iam.tf` | Roles de Lambda y Glue, política `fieldshift-gold-read` para la API |
