locals {
  lake_arn    = aws_s3_bucket.lake.arn
  results_arn = aws_s3_bucket.athena_results.arn
}

# ---------- Rol de las Lambdas de ingesta: escriben solo en raw/ ----------
data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ingest_lambda" {
  name               = "${var.project}-ingest-lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "ingest_lambda" {
  statement {
    sid       = "ListLake"
    actions   = ["s3:ListBucket"]
    resources = [local.lake_arn]
  }
  statement {
    sid       = "ReadWriteRaw"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:AbortMultipartUpload"]
    resources = ["${local.lake_arn}/raw/*"]
  }
  statement {
    sid       = "EarthdataSecret"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.earthdata.arn]
  }
  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = [for lg in aws_cloudwatch_log_group.ingest : "${lg.arn}:*"]
  }
}

resource "aws_iam_role_policy" "ingest_lambda" {
  name   = "ingest"
  role   = aws_iam_role.ingest_lambda.id
  policy = data.aws_iam_policy_document.ingest_lambda.json
}

# ---------- Rol de Glue: lee raw/silver, escribe silver/gold, catálogo, SSM, Athena (vistas) ----------
data "aws_iam_policy_document" "glue_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "glue" {
  name               = "${var.project}-glue"
  assume_role_policy = data.aws_iam_policy_document.glue_assume.json
}

data "aws_iam_policy_document" "glue" {
  statement {
    sid       = "ListBuckets"
    actions   = ["s3:ListBucket", "s3:GetBucketLocation"]
    resources = [local.lake_arn, local.results_arn]
  }
  statement {
    sid       = "ReadLake"
    actions   = ["s3:GetObject"]
    resources = ["${local.lake_arn}/raw/*", "${local.lake_arn}/silver/*", "${local.lake_arn}/gold/*", "${local.lake_arn}/code/*"]
  }
  statement {
    sid       = "WriteSilverGold"
    actions   = ["s3:PutObject", "s3:DeleteObject"]
    resources = ["${local.lake_arn}/silver/*", "${local.lake_arn}/gold/*"]
  }
  statement {
    sid       = "AthenaResults"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:AbortMultipartUpload"]
    resources = ["${local.results_arn}/*"]
  }
  statement {
    sid = "GlueCatalog"
    actions = [
      "glue:GetDatabase", "glue:GetDatabases",
      "glue:GetTable", "glue:GetTables", "glue:CreateTable", "glue:UpdateTable", "glue:DeleteTable",
      "glue:GetPartition", "glue:GetPartitions", "glue:BatchCreatePartition", "glue:BatchDeletePartition",
      "glue:CreatePartition", "glue:UpdatePartition", "glue:DeletePartition",
    ]
    resources = [
      "arn:aws:glue:${var.region}:${var.account_id}:catalog",
      aws_glue_catalog_database.silver.arn,
      aws_glue_catalog_database.gold.arn,
      "arn:aws:glue:${var.region}:${var.account_id}:table/${aws_glue_catalog_database.silver.name}/*",
      "arn:aws:glue:${var.region}:${var.account_id}:table/${aws_glue_catalog_database.gold.name}/*",
    ]
  }
  statement {
    sid       = "Athena"
    actions   = ["athena:StartQueryExecution", "athena:GetQueryExecution", "athena:GetQueryResults", "athena:GetWorkGroup"]
    resources = [aws_athena_workgroup.this.arn]
  }
  statement {
    sid       = "DataVersion"
    actions   = ["ssm:GetParameter", "ssm:PutParameter"]
    resources = [aws_ssm_parameter.data_version.arn]
  }
  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:${var.region}:${var.account_id}:log-group:/aws-glue/*"]
  }
}

resource "aws_iam_role_policy" "glue" {
  name   = "glue-etl"
  role   = aws_iam_role.glue.id
  policy = data.aws_iam_policy_document.glue.json
}

# ---------- Política de solo lectura para la API (BE la adjunta al rol de su servicio) ----------
# Permite consultar las vistas v_* de fieldshift_gold por Athena y leer la data_version. No da escritura al lake.
data "aws_iam_policy_document" "gold_read" {
  statement {
    sid = "AthenaQuery"
    actions = [
      "athena:StartQueryExecution", "athena:GetQueryExecution", "athena:GetQueryResults",
      "athena:StopQueryExecution", "athena:GetWorkGroup",
    ]
    resources = [aws_athena_workgroup.this.arn]
  }
  statement {
    sid = "GlueCatalogRead"
    actions = [
      "glue:GetDatabase", "glue:GetDatabases", "glue:GetTable", "glue:GetTables",
      "glue:GetPartition", "glue:GetPartitions",
    ]
    resources = [
      "arn:aws:glue:${var.region}:${var.account_id}:catalog",
      aws_glue_catalog_database.gold.arn,
      "arn:aws:glue:${var.region}:${var.account_id}:table/${aws_glue_catalog_database.gold.name}/*",
    ]
  }
  statement {
    sid       = "ListBuckets"
    actions   = ["s3:ListBucket", "s3:GetBucketLocation"]
    resources = [local.lake_arn, local.results_arn]
  }
  statement {
    sid       = "ReadGold"
    actions   = ["s3:GetObject"]
    resources = ["${local.lake_arn}/gold/*"]
  }
  statement {
    sid       = "AthenaResults"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:AbortMultipartUpload"]
    resources = ["${local.results_arn}/*"]
  }
  statement {
    sid       = "DataVersion"
    actions   = ["ssm:GetParameter"]
    resources = [aws_ssm_parameter.data_version.arn]
  }
}

resource "aws_iam_policy" "gold_read" {
  name        = "${var.project}-gold-read"
  description = "Solo lectura de fieldshift_gold por Athena y de /fieldshift/data_version (para la API)."
  policy      = data.aws_iam_policy_document.gold_read.json
}
