resource "aws_glue_catalog_database" "silver" {
  name        = "${var.project}_silver"
  description = "Field Shift silver: datos diarios limpios por celda (UTC, sin rellenos)."
}

resource "aws_glue_catalog_database" "gold" {
  name        = "${var.project}_gold"
  description = "Field Shift gold: indicadores por celda/decena/año + vistas v_* para la API."
}

resource "aws_athena_workgroup" "this" {
  name          = var.project
  force_destroy = true

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true
    bytes_scanned_cutoff_per_query     = var.athena_bytes_cutoff

    engine_version {
      selected_engine_version = "Athena engine version 3"
    }

    result_configuration {
      output_location = "s3://${aws_s3_bucket.athena_results.bucket}/results/"
      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }
}
