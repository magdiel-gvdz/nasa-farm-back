environment                      = "dev"
aws_region                       = "us-east-1"
project                          = "nasa-farm"
github_repository                = "magdiel-gvdz/nasa-farm-back"
runtime_permissions_boundary_arn = "arn:aws:iam::123456789012:policy/nasa-farm-runtime-boundary"
cors_origins                     = ["http://localhost:5173"]

ecr_repository_url     = "123456789012.dkr.ecr.us-east-1.amazonaws.com/nasa-farm-api"
image_tag              = "0123456789012345678901234567890123456789"
data_provider          = "fixture"
data_region            = "us-west-2"
data_lake_bucket       = null
athena_results_bucket  = null
athena_workgroup       = "fieldshift"
athena_database        = "fieldshift_gold"
data_version_parameter = "/fieldshift/data_version"
bedrock_model_id       = "anthropic.claude-3-haiku-20240307-v1:0"
