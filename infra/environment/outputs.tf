output "api_url" {
  value = "https://${trimprefix(one([for path in aws_ecs_express_gateway_service.api.ingress_paths : path.endpoint if path.access_type == "PUBLIC"]), "https://")}"
}
output "data_lake_bucket" {
  value = aws_s3_bucket.data_lake.id
}
output "environment" {
  value = var.environment
}
output "app_table" {
  value = aws_dynamodb_table.app.name
}
output "service_arn" {
  value = aws_ecs_express_gateway_service.api.service_arn
}
