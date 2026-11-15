aws_region                 = "us-east-1"
project                    = "nasa-farm"
github_repository          = "magdiel-gvdz/nasa-farm-back"
github_oidc_subject_prefix = "repo:magdiel-gvdz@124541175/nasa-farm-back@1457978584"
# Retrieve the prefix for your repository instead of assuming the legacy format:
# gh api repos/OWNER/REPO/actions/oidc/customization/sub --jq .sub_claim_prefix
# If the account already has a GitHub OIDC provider, reuse it:
# existing_github_oidc_provider_arn = "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"

# Recursos de DATA; null usa el nombre derivado de la cuenta.
data_region                   = "us-west-2"
data_lake_bucket              = null
athena_results_bucket         = null
athena_workgroup              = "fieldshift"
glue_database                 = "fieldshift_gold"
data_version_parameter_prefix = "/fieldshift/"
