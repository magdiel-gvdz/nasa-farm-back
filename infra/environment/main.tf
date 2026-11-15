data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

locals {
  data_lake_bucket      = coalesce(var.data_lake_bucket, "fieldshift-lake-${data.aws_caller_identity.current.account_id}")
  athena_results_bucket = coalesce(var.athena_results_bucket, "fieldshift-athena-results-${data.aws_caller_identity.current.account_id}")
  name                  = "${var.project}-${var.environment}"
  is_preview            = startswith(var.environment, "pr-")
  retention             = local.is_preview ? 3 : 30
}

resource "aws_s3_bucket" "data_lake" {
  bucket        = "${local.name}-data-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
  force_destroy = local.is_preview
}

resource "aws_s3_bucket_public_access_block" "data_lake" {
  bucket                  = aws_s3_bucket.data_lake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  versioning_configuration {
    status = local.is_preview ? "Suspended" : "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "data_lake" {
  bucket     = aws_s3_bucket.data_lake.id
  depends_on = [aws_s3_bucket_versioning.data_lake]
  rule {
    id     = "abort-incomplete-uploads"
    status = "Enabled"
    filter {}
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
  dynamic "rule" {
    for_each = local.is_preview ? [1] : []
    content {
      id     = "expire-preview-data"
      status = "Enabled"
      filter {}
      expiration {
        days = 7
      }
      noncurrent_version_expiration {
        noncurrent_days = 1
      }
    }
  }
  dynamic "rule" {
    for_each = local.is_preview ? [] : [1]
    content {
      id     = "expire-old-dev-versions"
      status = "Enabled"
      filter {}
      noncurrent_version_expiration {
        noncurrent_days = 90
      }
    }
  }
}

resource "aws_s3_bucket_policy" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource  = [aws_s3_bucket.data_lake.arn, "${aws_s3_bucket.data_lake.arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
}


resource "aws_iam_role" "api" {
  name                 = "${local.name}-api"
  permissions_boundary = var.runtime_permissions_boundary_arn
  tags                 = { Environment = var.environment }
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = "ecs-tasks.amazonaws.com" }
  }] })
}
resource "aws_dynamodb_table" "app" {
  name                        = "${local.name}-app"
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = "client_id"
  range_key                   = "sk"
  deletion_protection_enabled = !local.is_preview
  attribute {
    name = "client_id"
    type = "S"
  }
  attribute {
    name = "sk"
    type = "S"
  }
  # Los contadores de uso del chat caducan solos al día siguiente.
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }
}
resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${local.name}-api"
  retention_in_days = local.retention
}

resource "aws_iam_role_policy" "api" {
  name = "runtime"
  role = aws_iam_role.api.id
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Sid" : "ReadGold",
        "Effect" : "Allow",
        "Action" : [
          "s3:GetObject"
        ],
        "Resource" : [
          "arn:${data.aws_partition.current.partition}:s3:::${local.data_lake_bucket}/gold/*"
        ]
      },
      {
        "Sid" : "GoldBucketLocation",
        "Effect" : "Allow",
        "Action" : ["s3:GetBucketLocation"],
        "Resource" : ["arn:${data.aws_partition.current.partition}:s3:::${local.data_lake_bucket}"]
      },
      {
        "Sid" : "ListGold",
        "Effect" : "Allow",
        "Action" : [
          "s3:ListBucket"
        ],
        "Resource" : [
          "arn:${data.aws_partition.current.partition}:s3:::${local.data_lake_bucket}"
        ],
        "Condition" : {
          "StringLike" : {
            "s3:prefix" : [
              "gold",
              "gold/*"
            ]
          }
        }
      },
      {
        "Sid" : "AthenaQueries",
        "Effect" : "Allow",
        "Action" : [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:StopQueryExecution",
          "athena:GetWorkGroup"
        ],
        "Resource" : [
          "arn:${data.aws_partition.current.partition}:athena:${var.data_region}:${data.aws_caller_identity.current.account_id}:workgroup/${var.athena_workgroup}"
        ]
      },
      {
        "Sid" : "AthenaResults",
        "Effect" : "Allow",
        "Action" : [
          "s3:GetObject",
          "s3:PutObject",
          "s3:AbortMultipartUpload"
        ],
        "Resource" : [
          "arn:${data.aws_partition.current.partition}:s3:::${local.athena_results_bucket}/*"
        ]
      },
      {
        "Sid" : "AthenaResultsBucket",
        "Effect" : "Allow",
        "Action" : [
          "s3:GetBucketLocation",
          "s3:ListBucket"
        ],
        "Resource" : [
          "arn:${data.aws_partition.current.partition}:s3:::${local.athena_results_bucket}"
        ]
      },
      {
        "Sid" : "ReadCatalog",
        "Effect" : "Allow",
        "Action" : [
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:GetTable",
          "glue:GetTables",
          "glue:GetPartition",
          "glue:GetPartitions",
          "glue:BatchGetPartition"
        ],
        "Resource" : [
          "arn:${data.aws_partition.current.partition}:glue:${var.data_region}:${data.aws_caller_identity.current.account_id}:catalog",
          "arn:${data.aws_partition.current.partition}:glue:${var.data_region}:${data.aws_caller_identity.current.account_id}:database/${var.athena_database}",
          "arn:${data.aws_partition.current.partition}:glue:${var.data_region}:${data.aws_caller_identity.current.account_id}:table/${var.athena_database}/*"
        ]
      },
      {
        "Sid" : "ReadDataVersion",
        "Effect" : "Allow",
        "Action" : [
          "ssm:GetParameter"
        ],
        "Resource" : [
          "arn:${data.aws_partition.current.partition}:ssm:${var.data_region}:${data.aws_caller_identity.current.account_id}:parameter${var.data_version_parameter}"
        ]
      },
      {
        "Sid" : "InvokeChatModels",
        "Effect" : "Allow",
        "Action" : [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ],
        "Resource" : [
          "arn:${data.aws_partition.current.partition}:bedrock:${var.aws_region}::foundation-model/anthropic.*",
          "arn:${data.aws_partition.current.partition}:bedrock:${var.aws_region}::foundation-model/qwen.*",
          "arn:${data.aws_partition.current.partition}:bedrock:${var.aws_region}::foundation-model/amazon.nova-*"
        ]
      },
      {
        "Sid" : "OwnAppTable",
        "Effect" : "Allow",
        "Action" : [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem",
          "dynamodb:DescribeTable"
        ],
        "Resource" : [
          "${aws_dynamodb_table.app.arn}"
        ]
      },
      {
        "Sid" : "OwnAppObjects",
        "Effect" : "Allow",
        "Action" : [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ],
        "Resource" : [
          "${aws_s3_bucket.data_lake.arn}/uploads/*",
          "${aws_s3_bucket.data_lake.arn}/cache/*"
        ]
      }
    ]
  })
}

locals {
  platform_roles = {
    exec  = { principal = "ecs-tasks.amazonaws.com", policy = "AmazonECSTaskExecutionRolePolicy" }
    infra = { principal = "ecs.amazonaws.com", policy = "AmazonECSInfrastructureRoleforExpressGatewayServices" }
  }
  container_environment = {
    ENVIRONMENT            = var.environment
    CORS_ORIGINS           = jsonencode(var.cors_origins)
    APP_TABLE              = aws_dynamodb_table.app.name
    APP_BUCKET             = aws_s3_bucket.data_lake.id
    DATA_PROVIDER          = var.data_provider
    DATA_REGION            = var.data_region
    DATA_LAKE_BUCKET       = local.data_lake_bucket
    ATHENA_RESULTS_BUCKET  = local.athena_results_bucket
    ATHENA_WORKGROUP       = var.athena_workgroup
    ATHENA_DATABASE        = var.athena_database
    DATA_VERSION_PARAMETER = var.data_version_parameter
    BEDROCK_MODEL_ID       = var.bedrock_model_id
    CHAT_ENABLED           = tostring(var.chat_enabled)
    BEDROCK_REGION         = var.aws_region
    CHAT_RATE_PER_MINUTE   = tostring(var.chat_rate_per_minute)
    CHAT_RATE_PER_DAY      = tostring(local.is_preview ? min(var.chat_rate_per_day, 20) : var.chat_rate_per_day)
    CHAT_DAILY_BUDGET      = tostring(local.is_preview ? min(var.chat_daily_budget, 200) : var.chat_daily_budget)
    CHAT_MAX_OUTPUT_TOKENS = tostring(var.chat_max_output_tokens)
  }
}
resource "aws_iam_role" "platform" {
  for_each = local.platform_roles
  name     = "${local.name}-api-${each.key}"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = each.value.principal }
  }] })
}
resource "aws_iam_role_policy_attachment" "platform" {
  for_each   = local.platform_roles
  role       = aws_iam_role.platform[each.key].name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/${each.value.policy}"
}
resource "aws_ecs_express_gateway_service" "api" {
  service_name            = "${local.name}-api"
  execution_role_arn      = aws_iam_role.platform["exec"].arn
  infrastructure_role_arn = aws_iam_role.platform["infra"].arn
  task_role_arn           = aws_iam_role.api.arn
  cpu                     = "1024"
  memory                  = "2048"
  health_check_path       = "/health"
  wait_for_steady_state   = true
  primary_container {
    image          = "${var.ecr_repository_url}:${var.image_tag}"
    container_port = 8080
    aws_logs_configuration {
      log_group         = aws_cloudwatch_log_group.api.name
      log_stream_prefix = "api"
    }
    dynamic "environment" {
      for_each = local.container_environment
      content {
        name  = environment.key
        value = environment.value
      }
    }
  }
  scaling_target {
    # El proveedor rellena estos valores por defecto; declararlos evita el
    # error "inconsistent result after apply".
    min_task_count            = 1
    max_task_count            = local.is_preview ? 1 : 2
    auto_scaling_metric       = "AVERAGE_CPU"
    auto_scaling_target_value = 60
  }
  depends_on = [aws_iam_role_policy.api, aws_iam_role_policy_attachment.platform]
}
