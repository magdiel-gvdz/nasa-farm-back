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

variable "github_repository" {
  type    = string
  default = "magdiel-gvdz/nasa-farm-back"
  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "Use owner/repository."
  }
}

variable "existing_github_oidc_provider_arn" {
  type        = string
  default     = null
  description = "Reuse the account's GitHub OIDC provider if it already exists."
}

variable "github_oidc_subject_prefix" {
  type        = string
  default     = null
  description = "Exact sub_claim_prefix returned by GitHub's repository OIDC customization API. Null uses the legacy name-only format."
  validation {
    condition     = var.github_oidc_subject_prefix == null ? true : can(regex("^repo:[A-Za-z0-9_.-]+(@[0-9]+)?/[A-Za-z0-9_.-]+(@[0-9]+)?$", var.github_oidc_subject_prefix))
    error_message = "Use the exact repo:owner/repository or repo:owner@owner_id/repository@repository_id prefix."
  }
}

variable "data_region" {
  type    = string
  default = "us-west-2"
}

variable "data_lake_bucket" {
  type    = string
  default = null
}

variable "athena_results_bucket" {
  type    = string
  default = null
}

variable "athena_workgroup" {
  type    = string
  default = "fieldshift"
}

variable "glue_database" {
  type    = string
  default = "fieldshift_gold"
}

variable "data_version_parameter_prefix" {
  type    = string
  default = "/fieldshift/"
}
