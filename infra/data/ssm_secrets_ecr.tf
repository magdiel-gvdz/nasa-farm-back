# Versión vigente de gold. La escribe gold_build; Terraform no pisa el valor después de crearlo.
resource "aws_ssm_parameter" "data_version" {
  name        = "/${var.project}/data_version"
  type        = "String"
  value       = "none"
  description = "data_version vigente de gold (YYYYMMDDHH). La actualiza el job gold_build."

  lifecycle {
    ignore_changes = [value]
  }
}

# Solo el contenedor del secreto: el valor {username,password} se carga fuera de Terraform
# (aws secretsmanager put-secret-value) para que no quede en el estado.
resource "aws_secretsmanager_secret" "earthdata" {
  name                    = "${var.project}/earthdata"
  description             = "Earthdata Login para AppEEARS: {\"username\":...,\"password\":...}"
  recovery_window_in_days = 0
}

# Repositorio de la imagen única de las Lambdas de ingesta (arm64).
resource "aws_ecr_repository" "ingest" {
  name                 = "${var.project}-ingest"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "ingest" {
  repository = aws_ecr_repository.ingest.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Conservar las últimas 5 imágenes"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = { type = "expire" }
    }]
  })
}

# Log groups creados de antemano para fijar la retención (7 días).
locals {
  ingest_functions = ["ingest_power", "ingest_soil", "ingest_elevation", "appeears_submit", "appeears_poll"]
}

resource "aws_cloudwatch_log_group" "ingest" {
  for_each          = toset(local.ingest_functions)
  name              = "/aws/lambda/${var.project}-${replace(each.key, "_", "-")}"
  retention_in_days = var.log_retention_days
}
