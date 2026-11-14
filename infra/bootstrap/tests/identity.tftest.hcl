mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = { account_id = "123456789012" }
  }
  mock_data "aws_partition" {
    defaults = { partition = "aws" }
  }
}

run "protect_state_and_limit_oidc_subjects" {
  command = plan
  variables {
    existing_github_oidc_provider_arn = "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
  }
  assert {
    condition     = !aws_s3_bucket.state.force_destroy
    error_message = "The shared state bucket must never be force-deleted."
  }
  assert {
    condition     = jsondecode(aws_iam_role.deploy["dev"].assume_role_policy).Statement[0].Condition.StringEquals["token.actions.githubusercontent.com:sub"] == ["repo:magdiel-gvdz/nasa-farm-back:ref:refs/heads/main"]
    error_message = "Only main may assume the dev role."
  }
  assert {
    condition     = !strcontains(jsonencode(local.deployments.preview), "environments/dev")
    error_message = "Preview state access must not include dev."
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
