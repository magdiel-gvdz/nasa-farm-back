terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.80"
    }
  }

  # Estado remoto propio de DATA, separado del estado de la API. Los valores reales no se versionan:
  #   terraform init -backend-config=backend.hcl   (ver backend.example.hcl)
  backend "s3" {}
}

provider "aws" {
  region              = var.region
  allowed_account_ids = [var.account_id]

  default_tags {
    tags = {
      Project   = var.project
      Owner     = "data"
      ManagedBy = "terraform"
      Stack     = "fieldshift-data"
    }
  }
}
