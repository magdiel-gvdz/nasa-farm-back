mock_provider "aws" {
  override_during = plan
  mock_resource "aws_ecs_express_gateway_service" {
    defaults = {
      ingress_paths = [{ access_type = "PUBLIC", endpoint = "preview.example.com" }]
    }
  }
  mock_data "aws_caller_identity" {
    defaults = { account_id = "123456789012" }
  }
  mock_data "aws_partition" {
    defaults = { partition = "aws" }
  }
}

variables {
  runtime_permissions_boundary_arn = "arn:aws:iam::123456789012:policy/nasa-farm-runtime-boundary"
  ecr_repository_url               = "123456789012.dkr.ecr.us-east-1.amazonaws.com/nasa-farm-api"
  image_tag                        = "0123456789012345678901234567890123456789"
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
    condition     = local.container_environment.ENVIRONMENT == "dev"
    error_message = "Runtime must be bound to its own environment."
  }
  assert {
    condition     = aws_dynamodb_table.app.deletion_protection_enabled && aws_dynamodb_table.app.billing_mode == "PAY_PER_REQUEST"
    error_message = "La tabla de dev debe estar protegida y pagar por petición."
  }
  assert {
    condition     = aws_dynamodb_table.app.hash_key == "client_id" && aws_dynamodb_table.app.range_key == "sk"
    error_message = "La tabla debe usar las claves del contrato."
  }
  assert {
    condition     = aws_ecs_express_gateway_service.api.scaling_target[0].max_task_count == 2
    error_message = "Dev admite hasta dos tareas."
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
    condition     = aws_ecs_express_gateway_service.api.service_name == "nasa-farm-pr-42-api"
    error_message = "Every PR must have an isolated service."
  }
  assert {
    condition     = aws_cloudwatch_log_group.api.retention_in_days == 3
    error_message = "Preview logs must have short retention."
  }
  assert {
    condition     = !aws_dynamodb_table.app.deletion_protection_enabled && aws_dynamodb_table.app.name == "nasa-farm-pr-42-app"
    error_message = "La tabla de preview debe estar aislada y poder destruirse."
  }
  assert {
    condition     = aws_ecs_express_gateway_service.api.primary_container[0].image == "${var.ecr_repository_url}:${var.image_tag}" && aws_ecs_express_gateway_service.api.primary_container[0].container_port == 8080
    error_message = "La imagen desplegada debe coincidir con el SHA y escuchar en 8080."
  }
  assert {
    condition     = aws_ecs_express_gateway_service.api.health_check_path == "/health" && aws_ecs_express_gateway_service.api.wait_for_steady_state
    error_message = "El apply debe esperar un servicio sano."
  }
  assert {
    condition     = aws_ecs_express_gateway_service.api.cpu == "1024" && aws_ecs_express_gateway_service.api.memory == "2048" && aws_ecs_express_gateway_service.api.scaling_target[0].min_task_count == 1 && aws_ecs_express_gateway_service.api.scaling_target[0].max_task_count == 1
    error_message = "El preview ejecuta una tarea con 1 vCPU y 2 GiB."
  }
  assert {
    condition     = aws_iam_role.api.permissions_boundary == var.runtime_permissions_boundary_arn && jsondecode(aws_iam_role.api.assume_role_policy).Statement[0].Principal.Service == "ecs-tasks.amazonaws.com"
    error_message = "El rol de tarea debe conservar el límite."
  }
  assert {
    condition     = local.platform_roles.exec.policy == "AmazonECSTaskExecutionRolePolicy" && local.platform_roles.infra.policy == "AmazonECSInfrastructureRoleforExpressGatewayServices"
    error_message = "Los roles de plataforma deben usar las políticas oficiales."
  }
  assert {
    condition     = local.container_environment.DATA_PROVIDER == "fixture" && local.container_environment.DATA_REGION == "us-west-2" && local.container_environment.ENVIRONMENT == "pr-42" && local.container_environment.CHAT_ENABLED == "false"
    error_message = "El contenedor debe recibir su entorno y la configuración de DATA."
  }
}

run "athena_configuration" {
  command = plan
  variables {
    environment   = "pr-7"
    data_provider = "athena"
  }
  assert {
    condition     = local.container_environment.DATA_PROVIDER == "athena" && local.container_environment.ATHENA_DATABASE == "fieldshift_gold" && local.container_environment.DATA_VERSION_PARAMETER == "/fieldshift/data_version"
    error_message = "Cambiar a Athena no debe requerir cambiar la imagen."
  }
}

run "reject_unknown_provider" {
  command = plan
  variables {
    environment   = "dev"
    data_provider = "other"
  }
  expect_failures = [var.data_provider]
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
