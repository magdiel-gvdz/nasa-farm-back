data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

locals {
  data_parameter_prefix = trimprefix(var.data_version_parameter_prefix, "/")
  data_lake_bucket      = coalesce(var.data_lake_bucket, "fieldshift-lake-${data.aws_caller_identity.current.account_id}")
  athena_results_bucket = coalesce(var.athena_results_bucket, "fieldshift-athena-results-${data.aws_caller_identity.current.account_id}")
  account_id            = data.aws_caller_identity.current.account_id
  partition             = data.aws_partition.current.partition
  oidc_arn              = var.existing_github_oidc_provider_arn != null ? var.existing_github_oidc_provider_arn : aws_iam_openid_connect_provider.github[0].arn
  oidc_subject_prefix   = coalesce(var.github_oidc_subject_prefix, "repo:${var.github_repository}")
  deployments = {
    dev = {
      name_pattern = "${var.project}-dev"
      state_prefix = "environments/dev"
      subject      = "${local.oidc_subject_prefix}:ref:refs/heads/main"
    }
    preview = {
      name_pattern = "${var.project}-pr-*"
      state_prefix = "environments/pr-*"
      subject      = "${local.oidc_subject_prefix}:pull_request"
    }
  }
}

resource "aws_s3_bucket" "state" {
  bucket        = "${var.project}-tfstate-${local.account_id}-${var.aws_region}"
  force_destroy = false
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "state" {
  bucket = aws_s3_bucket.state.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource  = [aws_s3_bucket.state.arn, "${aws_s3_bucket.state.arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
}

resource "aws_iam_openid_connect_provider" "github" {
  count          = var.existing_github_oidc_provider_arn == null ? 1 : 0
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

# Even a modified inline policy cannot grant a Lambda execution role write access
# or access to IAM. CI cannot remove this boundary from the roles it creates.
resource "aws_iam_policy" "runtime_boundary" {
  name = "${var.project}-runtime-boundary"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:${local.partition}:logs:${var.aws_region}:${local.account_id}:log-group:/aws/lambda/${var.project}-*:log-stream:*"
      },
      {
        Effect = "Allow"
        Action = ["s3:GetObject"]
        Resource = [
          "arn:${local.partition}:s3:::${var.project}-*-data-${local.account_id}-${var.aws_region}/curated/*",
          "arn:${local.partition}:s3:::${var.project}-*-data-${local.account_id}-${var.aws_region}/manifests/*"
        ]
      },
      {
        "Sid" : "ReadGold",
        "Effect" : "Allow",
        "Action" : [
          "s3:GetObject"
        ],
        "Resource" : [
          "arn:${local.partition}:s3:::${local.data_lake_bucket}/gold/*"
        ]
      },
      {
        "Sid" : "GoldBucketLocation",
        "Effect" : "Allow",
        "Action" : ["s3:GetBucketLocation"],
        "Resource" : ["arn:${local.partition}:s3:::${local.data_lake_bucket}"]
      },
      {
        "Sid" : "ListGold",
        "Effect" : "Allow",
        "Action" : [
          "s3:ListBucket"
        ],
        "Resource" : [
          "arn:${local.partition}:s3:::${local.data_lake_bucket}"
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
          "arn:${local.partition}:athena:${var.data_region}:${local.account_id}:workgroup/${var.athena_workgroup}"
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
          "arn:${local.partition}:s3:::${local.athena_results_bucket}/*"
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
          "arn:${local.partition}:s3:::${local.athena_results_bucket}"
        ]
      },
      {
        "Sid" : "ReadCatalog",
        "Effect" : "Allow",
        "Action" : [
          "glue:GetDatabase",
          "glue:GetTable",
          "glue:GetTables",
          "glue:GetPartition",
          "glue:GetPartitions",
          "glue:BatchGetPartition"
        ],
        "Resource" : [
          "arn:${local.partition}:glue:${var.data_region}:${local.account_id}:catalog",
          "arn:${local.partition}:glue:${var.data_region}:${local.account_id}:database/${var.glue_database}",
          "arn:${local.partition}:glue:${var.data_region}:${local.account_id}:table/${var.glue_database}/*"
        ]
      },
      {
        "Sid" : "ReadDataVersion",
        "Effect" : "Allow",
        "Action" : [
          "ssm:GetParameter"
        ],
        "Resource" : [
          "arn:${local.partition}:ssm:${var.data_region}:${local.account_id}:parameter/${local.data_parameter_prefix}*"
        ]
      },
      {
        "Sid" : "InvokeAnthropic",
        "Effect" : "Allow",
        "Action" : [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ],
        "Resource" : [
          "arn:${local.partition}:bedrock:${var.aws_region}::foundation-model/anthropic.*"
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
          "arn:${local.partition}:dynamodb:${var.aws_region}:${local.account_id}:table/${var.project}-$${aws:PrincipalTag/Environment}-app"
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
          "arn:${local.partition}:s3:::${var.project}-$${aws:PrincipalTag/Environment}-data-${local.account_id}-${var.aws_region}/uploads/*",
          "arn:${local.partition}:s3:::${var.project}-$${aws:PrincipalTag/Environment}-data-${local.account_id}-${var.aws_region}/cache/*"
        ]
      },
      {
        "Sid" : "ECSLogs",
        "Effect" : "Allow",
        "Action" : [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        "Resource" : [
          "arn:${local.partition}:logs:${var.aws_region}:${local.account_id}:log-group:/ecs/${var.project}-$${aws:PrincipalTag/Environment}-api:log-stream:*"
        ]
      }
    ]
  })
}

resource "aws_iam_role" "deploy" {
  for_each = local.deployments
  name     = "${var.project}-github-${each.key}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRoleWithWebIdentity"
      Principal = { Federated = local.oidc_arn }
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          "token.actions.githubusercontent.com:sub" = each.key == "preview" ? [each.value.subject, local.deployments.dev.subject] : [each.value.subject]
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "deploy" {
  for_each = local.deployments
  name     = "terraform-deployment"
  role     = aws_iam_role.deploy[each.key].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListOwnState"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = aws_s3_bucket.state.arn
        # Terraform lists this otherwise unused workspace prefix during init.
        Condition = { StringLike = { "s3:prefix" = ["${each.value.state_prefix}/*", "env:/"] } }
      },
      {
        Sid      = "OwnStateAndLock"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = "${aws_s3_bucket.state.arn}/${each.value.state_prefix}/*"
      },
      {
        Sid    = "OwnDataLake"
        Effect = "Allow"
        Action = [
          "s3:CreateBucket", "s3:DeleteBucket", "s3:GetBucket*", "s3:ListBucket*",
          "s3:PutBucketTagging", "s3:PutBucketVersioning", "s3:PutBucketPublicAccessBlock",
          "s3:PutBucketPolicy", "s3:DeleteBucketPolicy", "s3:GetEncryptionConfiguration",
          "s3:PutEncryptionConfiguration", "s3:GetLifecycleConfiguration", "s3:PutLifecycleConfiguration",
          "s3:GetAccelerateConfiguration", "s3:GetReplicationConfiguration",
          "s3:DeleteObject", "s3:DeleteObjectVersion", "s3:GetObject", "s3:PutObject"
        ]
        Resource = [
          "arn:${local.partition}:s3:::${each.value.name_pattern}-data-${local.account_id}-${var.aws_region}",
          "arn:${local.partition}:s3:::${each.value.name_pattern}-data-${local.account_id}-${var.aws_region}/*"
        ]
      },
      {
        Sid    = "OwnFunctions"
        Effect = "Allow"
        Action = [
          "lambda:CreateFunction", "lambda:DeleteFunction", "lambda:GetFunction*",
          "lambda:GetRuntimeManagementConfig", "lambda:UpdateFunctionCode",
          "lambda:UpdateFunctionConfiguration", "lambda:ListVersionsByFunction",
          "lambda:GetPolicy", "lambda:AddPermission", "lambda:RemovePermission",
          "lambda:TagResource", "lambda:UntagResource", "lambda:ListTags"
        ]
        Resource = "arn:${local.partition}:lambda:${var.aws_region}:${local.account_id}:function:${each.value.name_pattern}-api"
      },
      {
        Sid    = "OwnLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup", "logs:DeleteLogGroup", "logs:PutRetentionPolicy",
          "logs:DeleteRetentionPolicy", "logs:ListTagsForResource", "logs:TagResource", "logs:UntagResource"
        ]
        Resource = [
          "arn:${local.partition}:logs:${var.aws_region}:${local.account_id}:log-group:/aws/lambda/${each.value.name_pattern}-api",
          "arn:${local.partition}:logs:${var.aws_region}:${local.account_id}:log-group:/aws/lambda/${each.value.name_pattern}-api:*",
          "arn:${local.partition}:logs:${var.aws_region}:${local.account_id}:log-group:/aws/apigateway/${each.value.name_pattern}",
          "arn:${local.partition}:logs:${var.aws_region}:${local.account_id}:log-group:/aws/apigateway/${each.value.name_pattern}:*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:DescribeLogGroups", "logs:CreateLogDelivery", "logs:GetLogDelivery",
          "logs:UpdateLogDelivery", "logs:DeleteLogDelivery", "logs:ListLogDeliveries",
          "logs:PutResourcePolicy", "logs:DescribeResourcePolicies"
        ]
        Resource  = "*"
        Condition = { StringEquals = { "aws:RequestedRegion" = var.aws_region } }
      },
      {
        Sid    = "HttpApiControlPlane"
        Effect = "Allow"
        Action = [
          "apigateway:GET", "apigateway:POST", "apigateway:PUT", "apigateway:PATCH", "apigateway:DELETE",
          "apigateway:TagResource", "apigateway:UntagResource"
        ]
        Resource = [
          "arn:${local.partition}:apigateway:${var.aws_region}::/apis",
          "arn:${local.partition}:apigateway:${var.aws_region}::/apis/*",
          "arn:${local.partition}:apigateway:${var.aws_region}::/tags/*"
        ]
      },
      {
        Sid      = "CreateBoundedExecutionRoles"
        Effect   = "Allow"
        Action   = ["iam:CreateRole"]
        Resource = "arn:${local.partition}:iam::${local.account_id}:role/${each.value.name_pattern}-api"
        Condition = {
          StringEquals = { "iam:PermissionsBoundary" = aws_iam_policy.runtime_boundary.arn }
        }
      },
      {
        Sid    = "ManageOwnExecutionRoles"
        Effect = "Allow"
        Action = [
          "iam:GetRole", "iam:DeleteRole", "iam:UpdateAssumeRolePolicy", "iam:TagRole", "iam:UntagRole",
          "iam:ListRolePolicies", "iam:ListAttachedRolePolicies", "iam:ListInstanceProfilesForRole",
          "iam:GetRolePolicy", "iam:PutRolePolicy", "iam:DeleteRolePolicy"
        ]
        Resource = "arn:${local.partition}:iam::${local.account_id}:role/${each.value.name_pattern}-api"
      },
      {
        Sid       = "PassOwnRoleOnlyToLambda"
        Effect    = "Allow"
        Action    = ["iam:PassRole"]
        Resource  = "arn:${local.partition}:iam::${local.account_id}:role/${each.value.name_pattern}-api"
        Condition = { StringEquals = { "iam:PassedToService" = "lambda.amazonaws.com" } }
      },
      {
        "Sid" : "ECRAuthentication",
        "Effect" : "Allow",
        "Action" : [
          "ecr:GetAuthorizationToken"
        ],
        "Resource" : [
          "*"
        ]
      },
      {
        "Sid" : "PublishAPIImage",
        "Effect" : "Allow",
        "Action" : [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage",
          "ecr:DescribeImages"
        ],
        "Resource" : [
          "${aws_ecr_repository.api.arn}"
        ]
      },
      {
        "Sid" : "OwnExpressService",
        "Effect" : "Allow",
        "Action" : [
          "ecs:CreateExpressGatewayService",
          "ecs:UpdateExpressGatewayService",
          "ecs:DeleteExpressGatewayService",
          "ecs:DescribeExpressGatewayService",
          "ecs:DescribeServices",
          "ecs:ListServiceDeployments",
          "ecs:TagResource",
          "ecs:UntagResource",
          "ecs:ListTagsForResource"
        ],
        "Resource" : [
          "arn:${local.partition}:ecs:${var.aws_region}:${local.account_id}:service/default/${each.value.name_pattern}-api"
        ]
      },
      {
        "Sid" : "OwnServiceDeployments",
        "Effect" : "Allow",
        "Action" : ["ecs:DescribeServiceDeployments"],
        "Resource" : ["arn:${local.partition}:ecs:${var.aws_region}:${local.account_id}:service-deployment/default/${each.value.name_pattern}-api/*"]
      },
      {
        "Sid" : "ReadServiceSecurityGroups",
        "Effect" : "Allow",
        "Action" : ["ec2:DescribeSecurityGroups"],
        "Resource" : "*",
        "Condition" : { "StringEquals" : { "aws:RequestedRegion" : var.aws_region } }
      },
      {
        "Sid" : "ReadDefaultCluster",
        "Effect" : "Allow",
        "Action" : [
          "ecs:DescribeClusters", "ecs:CreateCluster"
        ],
        "Resource" : [
          "arn:${local.partition}:ecs:${var.aws_region}:${local.account_id}:cluster/default"
        ]
      },
      {
        "Sid" : "OwnTaskDefinitions",
        "Effect" : "Allow",
        "Action" : [
          "ecs:RegisterTaskDefinition",
          "ecs:DescribeTaskDefinition",
          "ecs:DeregisterTaskDefinition",
          "ecs:TagResource",
          "ecs:UntagResource",
          "ecs:ListTagsForResource"
        ],
        "Resource" : [
          "arn:${local.partition}:ecs:${var.aws_region}:${local.account_id}:task-definition/default-${each.value.name_pattern}-api:*"
        ]
      },
      {
        "Sid" : "OwnAppTable",
        "Effect" : "Allow",
        "Action" : [
          "dynamodb:CreateTable",
          "dynamodb:DeleteTable",
          "dynamodb:DescribeTable",
          "dynamodb:UpdateTable",
          "dynamodb:DescribeContinuousBackups",
          "dynamodb:DescribeTimeToLive",
          "dynamodb:ListTagsOfResource",
          "dynamodb:TagResource",
          "dynamodb:UntagResource"
        ],
        "Resource" : [
          "arn:${local.partition}:dynamodb:${var.aws_region}:${local.account_id}:table/${each.value.name_pattern}-app"
        ]
      },
      {
        "Sid" : "CreatePlatformRoles",
        "Effect" : "Allow",
        "Action" : [
          "iam:CreateRole"
        ],
        "Resource" : [
          "arn:${local.partition}:iam::${local.account_id}:role/${each.value.name_pattern}-api-exec",
          "arn:${local.partition}:iam::${local.account_id}:role/${each.value.name_pattern}-api-infra"
        ]
      },
      {
        "Sid" : "ManagePlatformRoles",
        "Effect" : "Allow",
        "Action" : [
          "iam:GetRole",
          "iam:DeleteRole",
          "iam:UpdateAssumeRolePolicy",
          "iam:TagRole",
          "iam:UntagRole",
          "iam:ListRolePolicies",
          "iam:ListAttachedRolePolicies",
          "iam:ListInstanceProfilesForRole"
        ],
        "Resource" : [
          "arn:${local.partition}:iam::${local.account_id}:role/${each.value.name_pattern}-api-exec",
          "arn:${local.partition}:iam::${local.account_id}:role/${each.value.name_pattern}-api-infra"
        ]
      },
      {
        "Sid" : "ExecutionManagedPolicy",
        "Effect" : "Allow",
        "Action" : [
          "iam:AttachRolePolicy",
          "iam:DetachRolePolicy"
        ],
        "Resource" : [
          "arn:${local.partition}:iam::${local.account_id}:role/${each.value.name_pattern}-api-exec"
        ],
        "Condition" : {
          "ArnEquals" : {
            "iam:PolicyARN" : "arn:${local.partition}:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
          }
        }
      },
      {
        "Sid" : "InfrastructureManagedPolicy",
        "Effect" : "Allow",
        "Action" : [
          "iam:AttachRolePolicy",
          "iam:DetachRolePolicy"
        ],
        "Resource" : [
          "arn:${local.partition}:iam::${local.account_id}:role/${each.value.name_pattern}-api-infra"
        ],
        "Condition" : {
          "ArnEquals" : {
            "iam:PolicyARN" : "arn:${local.partition}:iam::aws:policy/service-role/AmazonECSInfrastructureRoleforExpressGatewayServices"
          }
        }
      },
      {
        "Sid" : "PassTaskRoles",
        "Effect" : "Allow",
        "Action" : [
          "iam:PassRole"
        ],
        "Resource" : [
          "arn:${local.partition}:iam::${local.account_id}:role/${each.value.name_pattern}-api",
          "arn:${local.partition}:iam::${local.account_id}:role/${each.value.name_pattern}-api-exec"
        ],
        "Condition" : {
          "StringEquals" : {
            "iam:PassedToService" : ["ecs-tasks.amazonaws.com", "ecs.amazonaws.com"]
          }
        }
      },
      {
        "Sid" : "PassInfrastructureRole",
        "Effect" : "Allow",
        "Action" : [
          "iam:PassRole"
        ],
        "Resource" : [
          "arn:${local.partition}:iam::${local.account_id}:role/${each.value.name_pattern}-api-infra"
        ],
        "Condition" : {
          "StringEquals" : {
            "iam:PassedToService" : "ecs.amazonaws.com"
          }
        }
      },
      {
        "Sid" : "OwnECSLogs",
        "Effect" : "Allow",
        "Action" : [
          "logs:CreateLogGroup",
          "logs:DeleteLogGroup",
          "logs:PutRetentionPolicy",
          "logs:DeleteRetentionPolicy",
          "logs:ListTagsForResource",
          "logs:TagResource",
          "logs:UntagResource"
        ],
        "Resource" : [
          "arn:${local.partition}:logs:${var.aws_region}:${local.account_id}:log-group:/ecs/${each.value.name_pattern}-api",
          "arn:${local.partition}:logs:${var.aws_region}:${local.account_id}:log-group:/ecs/${each.value.name_pattern}-api:*"
        ]
      }
    ]
  })
}

# Prerrequisito de cuenta: CI solo administra los tres roles de cada entorno.
resource "aws_iam_service_linked_role" "ecs" {
  aws_service_name = "ecs.amazonaws.com"
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_ecr_repository" "api" {
  name                 = "${var.project}-api"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
}
resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name
  policy = jsonencode({ rules = [{
    rulePriority = 1
    description  = "Conservar las últimas 30 imágenes"
    selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 30 }
    action       = { type = "expire" }
  }] })
}
