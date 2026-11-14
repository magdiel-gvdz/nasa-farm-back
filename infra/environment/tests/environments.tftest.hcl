mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = { account_id = "123456789012" }
  }
  mock_data "aws_partition" {
    defaults = { partition = "aws" }
  }
}

variables {
  runtime_permissions_boundary_arn = "arn:aws:iam::123456789012:policy/nasa-farm-runtime-boundary"
}

run "dev_is_persistent" {
  command = plan
  variables {
    environment = "dev"
  }
  assert {
    condition     = !aws_s3_bucket.data_lake.force_destroy
    error_message = "Dev data must not be force-deleted."
  }
  assert {
    condition     = aws_s3_bucket_versioning.data_lake.versioning_configuration[0].status == "Enabled"
    error_message = "Dev data must be versioned."
  }
  assert {
    condition     = aws_cloudwatch_log_group.api.retention_in_days == 30
    error_message = "Dev logs must be retained for 30 days."
  }
  assert {
    condition     = aws_lambda_function.api.environment[0].variables.ENVIRONMENT == "dev"
    error_message = "Runtime must be bound to its own environment."
  }
}

run "preview_is_isolated_and_disposable" {
  command = plan
  variables {
    environment = "pr-42"
  }
  assert {
    condition     = aws_s3_bucket.data_lake.force_destroy
    error_message = "PR data must be removable when the PR closes."
  }
  assert {
    condition     = aws_s3_bucket.data_lake.bucket == "nasa-farm-pr-42-data-123456789012-us-east-1"
    error_message = "Every PR must have an isolated data lake."
  }
  assert {
    condition     = aws_lambda_function.api.function_name == "nasa-farm-pr-42-api"
    error_message = "Every PR must have an isolated function."
  }
  assert {
    condition     = aws_cloudwatch_log_group.api.retention_in_days == 3
    error_message = "Preview logs must have short retention."
  }
}

run "reject_permanent_environments_other_than_dev" {
  command = plan
  variables {
    environment = "production"
  }
  expect_failures = [var.environment]
}

run "reject_wildcard_cors" {
  command = plan
  variables {
    environment  = "dev"
    cors_origins = ["*"]
  }
  expect_failures = [var.cors_origins]
}
