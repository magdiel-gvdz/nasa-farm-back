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
      origin == "*" || can(regex("^https?://[^/ *]+(:[0-9]+)?$", origin))
    ])
    error_message = "Use orígenes HTTP(S) sin rutas, o * para permitir cualquier origen."
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

variable "athena_database" {
  type    = string
  default = "fieldshift_gold"
}

variable "data_version_parameter" {
  type    = string
  default = "/fieldshift/data_version"
}

variable "bedrock_model_id" {
  type    = string
  default = "mistral.mistral-large-3-675b-instruct"
}

variable "image_tag" {
  type = string
  validation {
    condition     = can(regex("^[a-f0-9]{40}$", var.image_tag))
    error_message = "Use una etiqueta de 40 caracteres hexadecimales."
  }
}
variable "ecr_repository_url" {
  type = string
  validation {
    condition     = can(regex("^[0-9]{12}\\.dkr\\.ecr\\.[a-z0-9-]+\\.amazonaws\\.com/[a-z0-9/_-]+$", var.ecr_repository_url))
    error_message = "Use la URL de un repositorio ECR privado, sin etiqueta."
  }
}
variable "data_provider" {
  type    = string
  default = "fixture"
  validation {
    condition     = contains(["fixture", "athena"], var.data_provider)
    error_message = "Use fixture o athena."
  }
}
variable "chat_enabled" {
  type    = bool
  default = false
}

variable "chat_rate_per_minute" {
  type        = number
  default     = 6
  description = "Mensajes de chat por cliente y minuto."
}

variable "chat_rate_per_day" {
  type        = number
  default     = 80
  description = "Mensajes de chat por cliente y día (en previews, como mucho 20)."
}

variable "chat_daily_budget" {
  type        = number
  default     = 1500
  description = "Mensajes de chat de todos los clientes por día (en previews, como mucho 200)."
}

variable "chat_max_output_tokens" {
  type        = number
  default     = 2048
  description = "Tokens máximos de cada respuesta del asistente."
}

