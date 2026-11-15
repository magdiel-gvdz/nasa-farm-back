# Lambdas de ingesta: una imagen (ECR fieldshift-ingest), un handler por fuente.
# ingest_power e ingest_soil se invocan a mano; appeears_poll corre cada 15 min mientras haya tareas pendientes.
data "aws_ecr_image" "ingest" {
  repository_name = aws_ecr_repository.ingest.name
  image_tag       = var.ingest_image_tag
}

locals {
  ingest_lambdas = {
    ingest_power     = { handler = "ingest.handlers.power.handler", memory = 1024 }
    ingest_soil      = { handler = "ingest.handlers.soil.handler", memory = 2048 }
    ingest_elevation = { handler = "ingest.handlers.elevation.handler", memory = 2048 }
    appeears_poll    = { handler = "ingest.handlers.appeears_poll.handler", memory = 1024 }
  }
}

resource "aws_lambda_function" "ingest" {
  for_each = local.ingest_lambdas

  function_name = "${var.project}-${replace(each.key, "_", "-")}"
  role          = aws_iam_role.ingest_lambda.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.ingest.repository_url}@${data.aws_ecr_image.ingest.image_digest}"
  architectures = ["arm64"]
  timeout       = 900
  memory_size   = each.value.memory

  image_config {
    command = [each.value.handler]
  }

  environment {
    variables = {
      LAKE_BUCKET         = aws_s3_bucket.lake.bucket
      EARTHDATA_SECRET_ID = aws_secretsmanager_secret.earthdata.name
    }
  }

  depends_on = [aws_cloudwatch_log_group.ingest, aws_iam_role_policy.ingest_lambda]
}

output "ingest_lambdas" {
  value = [for f in aws_lambda_function.ingest : f.function_name]
}

# appeears_poll cada 15 min. Cuando todo esté en raw, poner appeears_poll_enabled = false y aplicar.
resource "aws_cloudwatch_event_rule" "appeears_poll" {
  name                = "${var.project}-appeears-poll"
  description         = "Revisa las tareas de AppEEARS y baja los resultados a raw/appeears/"
  schedule_expression = "rate(15 minutes)"
  state               = var.appeears_poll_enabled ? "ENABLED" : "DISABLED"
}

resource "aws_cloudwatch_event_target" "appeears_poll" {
  rule = aws_cloudwatch_event_rule.appeears_poll.name
  arn  = aws_lambda_function.ingest["appeears_poll"].arn
}

resource "aws_lambda_permission" "appeears_poll_events" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest["appeears_poll"].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.appeears_poll.arn
}
