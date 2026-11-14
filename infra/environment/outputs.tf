output "api_url" {
  value = aws_apigatewayv2_stage.api.invoke_url
}

output "data_lake_bucket" {
  value = aws_s3_bucket.data_lake.id
}

output "environment" {
  value = var.environment
}

output "lambda_function_name" {
  value = aws_lambda_function.api.function_name
}
