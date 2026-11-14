variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project" {
  type    = string
  default = "nasa-farm"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,19}$", var.project))
    error_message = "Use 3-20 lowercase letters, numbers or hyphens, starting with a letter."
  }
}

variable "environment" {
  type        = string
  description = "Only dev is permanent. Preview environments must be named pr-<number>."
  validation {
    condition     = can(regex("^(dev|pr-[1-9][0-9]*)$", var.environment))
    error_message = "Environment must be dev or pr-<positive PR number>."
  }
}

variable "github_repository" {
  type    = string
  default = "magdiel-gvdz/nasa-farm-back"
}

variable "lambda_zip_path" {
  type    = string
  default = "../../build/api.zip"
}

variable "runtime_permissions_boundary_arn" {
  type        = string
  description = "Execution-role boundary created by the bootstrap stack."
}

variable "cors_origins" {
  type    = list(string)
  default = ["http://localhost:5173"]
  validation {
    condition = alltrue([
      for origin in var.cors_origins :
      can(regex("^https?://[^/ *]+(:[0-9]+)?$", origin)) && !strcontains(origin, "*")
    ])
    error_message = "CORS origins must be explicit HTTP(S) origins without paths or wildcards."
  }
}
