output "state_bucket" {
  value = aws_s3_bucket.state.id
}

output "dev_role_arn" {
  value = aws_iam_role.deploy["dev"].arn
}

output "preview_role_arn" {
  value = aws_iam_role.deploy["preview"].arn
}

output "runtime_permissions_boundary_arn" {
  value = aws_iam_policy.runtime_boundary.arn
}

output "backend_config" {
  value = <<-EOT
    bucket       = "${aws_s3_bucket.state.id}"
    key          = "bootstrap/terraform.tfstate"
    region       = "${var.aws_region}"
    encrypt      = true
    use_lockfile = true
  EOT
}
