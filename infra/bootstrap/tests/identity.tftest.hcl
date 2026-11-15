mock_provider "aws" {
  override_during = plan
  mock_data "aws_caller_identity" {
    defaults = { account_id = "123456789012" }
  }
  mock_data "aws_partition" {
    defaults = { partition = "aws" }
  }
}

run "protect_state_and_limit_oidc_subjects" {
  # Apply simulado para resolver los ARN usados dentro de las políticas JSON.
  command = apply
  variables {
    existing_github_oidc_provider_arn = "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
  }
  assert {
    condition     = !aws_s3_bucket.state.force_destroy
    error_message = "The shared state bucket must never be force-deleted."
  }
  assert {
    condition     = aws_iam_service_linked_role.ecs.aws_service_name == "ecs.amazonaws.com"
    error_message = "Bootstrap debe preparar el rol vinculado al servicio que ECS necesita en la cuenta."
  }
  assert {
    condition     = jsondecode(aws_iam_role.deploy["dev"].assume_role_policy).Statement[0].Condition.StringEquals["token.actions.githubusercontent.com:sub"] == ["repo:magdiel-gvdz/nasa-farm-back:ref:refs/heads/main"]
    error_message = "Only main may assume the dev role."
  }
  assert {
    condition     = !strcontains(jsonencode(local.deployments.preview), "environments/dev")
    error_message = "Preview state access must not include dev."
  }
  assert {
    condition     = aws_ecr_repository.api.image_tag_mutability == "IMMUTABLE" && aws_ecr_repository.api.image_scanning_configuration[0].scan_on_push && jsondecode(aws_ecr_lifecycle_policy.api.policy).rules[0].selection.countNumber == 30
    error_message = "ECR debe conservar 30 imágenes, escanearlas y rechazar etiquetas repetidas."
  }
  assert {
    condition     = length([for s in jsondecode(aws_iam_role_policy.deploy["preview"].policy).Statement : s if try(s.Sid, "") == "OwnFunctions" || try(s.Sid, "") == "HttpApiControlPlane"]) == 2
    error_message = "Los permisos heredados deben mantenerse durante la migración."
  }
  assert {
    condition     = one([for s in jsondecode(aws_iam_role_policy.deploy["preview"].policy).Statement : s.Resource if try(s.Sid, "") == "OwnAppTable"])[0] == "arn:aws:dynamodb:us-east-1:123456789012:table/nasa-farm-pr-*-app"
    error_message = "Preview no debe administrar la tabla de dev."
  }
  assert {
    condition     = one([for s in jsondecode(aws_iam_role_policy.deploy["preview"].policy).Statement : s.Condition.StringEquals["iam:PermissionsBoundary"] if try(s.Sid, "") == "CreateBoundedExecutionRoles"]) == aws_iam_policy.runtime_boundary.arn
    error_message = "CI no puede crear el rol de tarea sin límite."
  }
  assert {
    condition     = alltrue([for s in jsondecode(aws_iam_policy.runtime_boundary.policy).Statement : alltrue([for action in s.Action : !startswith(action, "iam:")])])
    error_message = "La API no puede administrar IAM."
  }
  assert {
    condition     = one([for s in jsondecode(aws_iam_policy.runtime_boundary.policy).Statement : s.Action if try(s.Sid, "") == "ReadGold"]) == ["s3:GetObject"]
    error_message = "El lake de DATA debe ser de solo lectura."
  }
  assert {
    condition     = one([for s in jsondecode(aws_iam_role_policy.deploy["preview"].policy).Statement : s.Condition.ArnEquals["iam:PolicyARN"] if try(s.Sid, "") == "ExecutionManagedPolicy"]) == "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
    error_message = "El rol de ejecución no puede recibir políticas arbitrarias."
  }
  assert {
    condition     = one([for s in jsondecode(aws_iam_role_policy.deploy["preview"].policy).Statement : s.Resource if try(s.Sid, "") == "OwnExpressService"]) == ["arn:aws:ecs:us-east-1:123456789012:service/default/nasa-farm-pr-*-api"]
    error_message = "Preview no debe administrar servicios de dev."
  }
  assert {
    condition     = length(aws_iam_role_policy.deploy["preview"].policy) <= 10240 && length(aws_iam_policy.runtime_boundary.policy) <= 6144
    error_message = "Las políticas deben caber en los límites de IAM."
  }
  assert {
    condition     = one([for s in jsondecode(aws_iam_role_policy.deploy["preview"].policy).Statement : s.Resource if try(s.Sid, "") == "PublishAPIImage"]) == [aws_ecr_repository.api.arn] && one([for s in jsondecode(aws_iam_role_policy.deploy["preview"].policy).Statement : s.Action if try(s.Sid, "") == "ECRAuthentication"]) == ["ecr:GetAuthorizationToken"]
    error_message = "La publicación de imágenes debe quedar limitada al repositorio compartido."
  }
  assert {
    condition     = toset(one([for s in jsondecode(aws_iam_role_policy.deploy["preview"].policy).Statement : s.Condition.StringEquals["iam:PassedToService"] if try(s.Sid, "") == "PassTaskRoles"])) == toset(["ecs-tasks.amazonaws.com", "ecs.amazonaws.com"]) && one([for s in jsondecode(aws_iam_role_policy.deploy["preview"].policy).Statement : s.Condition.StringEquals["iam:PassedToService"] if try(s.Sid, "") == "PassInfrastructureRole"]) == "ecs.amazonaws.com"
    error_message = "PassRole debe estar condicionado al servicio de ECS correspondiente."
  }
  assert {
    condition     = one([for s in jsondecode(aws_iam_role_policy.deploy["preview"].policy).Statement : s.Resource if try(s.Sid, "") == "ManageOwnExecutionRoles"]) == "arn:aws:iam::123456789012:role/nasa-farm-pr-*-api"
    error_message = "Los permisos de políticas en línea no deben incluir roles de plataforma."
  }
  assert {
    condition     = strcontains(one([for s in jsondecode(aws_iam_policy.runtime_boundary.policy).Statement : s.Resource[0] if try(s.Sid, "") == "OwnAppTable"]), "$${aws:PrincipalTag/Environment}")
    error_message = "El límite debe aislar la tabla por la etiqueta del entorno de la tarea."
  }
  assert {
    condition     = toset(one([for s in jsondecode(aws_iam_role_policy.deploy["dev"].policy).Statement : s.Resource if try(s.Sid, "") == "CreatePlatformRoles"])) == toset(["arn:aws:iam::123456789012:role/nasa-farm-dev-api-exec", "arn:aws:iam::123456789012:role/nasa-farm-dev-api-infra"])
    error_message = "Los permisos de dev deben coincidir con los nombres exactos de los roles de ECS."
  }
  assert {
    condition     = toset(one([for s in jsondecode(aws_iam_role_policy.deploy["dev"].policy).Statement : s.Resource if try(s.Sid, "") == "PassTaskRoles"])) == toset(["arn:aws:iam::123456789012:role/nasa-farm-dev-api", "arn:aws:iam::123456789012:role/nasa-farm-dev-api-exec"])
    error_message = "Dev solo debe pasar los roles de tarea y ejecución previstos para la API."
  }
  assert {
    condition     = one([for s in jsondecode(aws_iam_role_policy.deploy["preview"].policy).Statement : s.Resource if try(s.Sid, "") == "OwnTaskDefinitions"]) == ["arn:aws:ecs:us-east-1:123456789012:task-definition/default-nasa-farm-pr-*-api:*"]
    error_message = "Express Mode antepone el nombre del clúster default a la familia de tareas del entorno."
  }
  assert {
    condition     = contains(one([for s in jsondecode(aws_iam_role_policy.deploy["preview"].policy).Statement : s.Action if try(s.Sid, "") == "OwnExpressService"]), "ecs:ListServiceDeployments") && one([for s in jsondecode(aws_iam_role_policy.deploy["preview"].policy).Statement : s.Resource if try(s.Sid, "") == "OwnServiceDeployments"]) == ["arn:aws:ecs:us-east-1:123456789012:service-deployment/default/nasa-farm-pr-*-api/*"]
    error_message = "Terraform debe poder seguir únicamente los despliegues del servicio de su entorno."
  }
}

run "reuse_an_existing_oidc_provider" {
  command = plan
  variables {
    existing_github_oidc_provider_arn = "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
  }
  assert {
    condition     = length(aws_iam_openid_connect_provider.github) == 0
    error_message = "Do not attempt to create an OIDC provider that already exists."
  }
}

run "immutable_subjects_match_only_the_repository_and_allowed_contexts" {
  command = plan
  variables {
    existing_github_oidc_provider_arn = "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
    github_oidc_subject_prefix        = "repo:magdiel-gvdz@124541175/nasa-farm-back@1457978584"
  }
  assert {
    condition     = jsondecode(aws_iam_role.deploy["dev"].assume_role_policy).Statement[0].Condition.StringEquals["token.actions.githubusercontent.com:sub"] == ["repo:magdiel-gvdz@124541175/nasa-farm-back@1457978584:ref:refs/heads/main"]
    error_message = "Dev must accept the immutable repository identity only on main."
  }
  assert {
    condition = jsondecode(aws_iam_role.deploy["preview"].assume_role_policy).Statement[0].Condition.StringEquals["token.actions.githubusercontent.com:sub"] == [
      "repo:magdiel-gvdz@124541175/nasa-farm-back@1457978584:pull_request",
      "repo:magdiel-gvdz@124541175/nasa-farm-back@1457978584:ref:refs/heads/main"
    ]
    error_message = "Preview must accept the exact immutable PR identity and main cleanup context."
  }
}
