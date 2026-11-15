# Jobs de Glue Python shell (3.9, 1 DPU = 16 GB). Etapa 2 (C4): power_square_daily = 84 cuadros x 12,784 días
# (~1.07 M filas); gold calcula indicadores de ~3,000 celdas en tandas de 200 (tope 60 min). El código sale del repo:
#   scripts/package_glue.py -> build/fieldshift_glue.zip (glue/lib + config en JSON)
locals {
  repo_root     = "${path.module}/../.."
  glue_code_zip = "code/fieldshift_glue.zip"
  glue_jobs = {
    silver_build = { script = "silver_build.py", timeout = 30, args = { "--SOURCE" = "all" } }
    gold_build = {
      script  = "gold_build.py"
      timeout = 60
      args = {
        "--SSM_PARAMETER" = aws_ssm_parameter.data_version.name
        "--WORKGROUP"     = aws_athena_workgroup.this.name
      }
    }
  }
}

resource "aws_s3_object" "glue_code_zip" {
  bucket      = aws_s3_bucket.lake.id
  key         = local.glue_code_zip
  source      = "${local.repo_root}/build/fieldshift_glue.zip"
  source_hash = filemd5("${local.repo_root}/build/fieldshift_glue.zip")
}

resource "aws_s3_object" "glue_script" {
  for_each    = local.glue_jobs
  bucket      = aws_s3_bucket.lake.id
  key         = "code/jobs/${each.value.script}"
  source      = "${local.repo_root}/glue/jobs/${each.value.script}"
  source_hash = filemd5("${local.repo_root}/glue/jobs/${each.value.script}")
}

resource "aws_glue_job" "this" {
  for_each = local.glue_jobs

  name         = "${var.project}-${replace(each.key, "_", "-")}"
  role_arn     = aws_iam_role.glue.arn
  max_capacity = 1
  max_retries  = 0
  timeout      = each.value.timeout

  command {
    name            = "pythonshell"
    python_version  = "3.9"
    script_location = "s3://${aws_s3_bucket.lake.id}/${aws_s3_object.glue_script[each.key].key}"
  }

  default_arguments = merge({
    "library-set"    = "analytics"
    "--LAKE_BUCKET"  = aws_s3_bucket.lake.id
    "--CODE_ZIP"     = local.glue_code_zip
    "--DATA_VERSION" = "auto"
  }, each.value.args)
}

output "glue_jobs" {
  value = [for j in aws_glue_job.this : j.name]
}
