############################################
# Terraform and provider version baseline
############################################

terraform {
  # Keep the example pinned to the same Terraform CLI version line used across
  # the repository so example validation matches module validation.
  required_version = "~> 1.14.0"

  required_providers {
    aws = {
      # Pin the AWS provider to the same stable version line used by the module.
      source  = "hashicorp/aws"
      version = "~> 6.37"
    }

    random = {
      # The module declares random_id even when a caller provides an explicit
      # state_bucket_name, so the example keeps provider constraints complete.
      source  = "hashicorp/random"
      version = "~> 3.8"
    }
  }
}
