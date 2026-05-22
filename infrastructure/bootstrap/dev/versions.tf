############################################
# Terraform and provider version baseline
############################################

terraform {
  # Keep the bootstrap root pinned to the same Terraform CLI version line used by
  # infrastructure/envs/dev and the current reusable modules.
  required_version = "~> 1.14.0"

  required_providers {
    aws = {
      # Pin the AWS provider to the same stable version line used by
      # infrastructure/envs/dev and the current reusable modules.
      source  = "hashicorp/aws"
      version = "~> 6.37"
    }

    local = {
      # The bootstrap root writes the generated backend.tf file for envs/dev
      # after the remote state bucket exists.
      source  = "hashicorp/local"
      version = "~> 2.5"
    }

    random = {
      # The dev backend bucket can derive a globally unique name with a short
      # random suffix when no explicit state bucket name is provided.
      source  = "hashicorp/random"
      version = "~> 3.8"
    }
  }
}
