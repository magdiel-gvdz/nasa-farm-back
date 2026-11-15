variable "region" {
  description = "Región de la infraestructura de datos (pendiente de alinear con la API, que está en us-east-1)."
  type        = string
  default     = "us-west-2"
}

variable "account_id" {
  description = "Cuenta de AWS donde vive la pila de datos (se pasa por -var o por un tfvars no versionado)."
  type        = string
}

variable "project" {
  type    = string
  default = "fieldshift"
}

variable "athena_bytes_cutoff" {
  description = "Máximo de bytes escaneados por consulta en el workgroup (1 GB)."
  type        = number
  default     = 1073741824
}

variable "log_retention_days" {
  type    = number
  default = 7
}

variable "ingest_image_tag" {
  description = "Tag de la imagen de ingesta en ECR; Terraform fija el digest de ese tag."
  type        = string
  default     = "latest"
}

variable "appeears_poll_enabled" {
  description = "Programa appeears_poll cada 15 min; apagar cuando todas las tareas estén en raw."
  type        = bool
  default     = true
}
