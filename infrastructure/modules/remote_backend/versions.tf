############################################
# Terraform and provider version baseline
############################################

terraform {
  # Keep the module pinned to the same Terraform CLI version line used across
  # the repository so validation stays consistent between modules and env roots.
  required_version = "~> 1.14.0"

  required_providers {
    aws = {
      # Pin the AWS provider to the same stable version line used by the
      # existing infrastructure modules and environments.
      source  = "hashicorp/aws"
      version = "~> 6.37"
    }

    random = {
      # The backend bucket can derive a globally unique name with a short random
      # suffix when callers do not provide an explicit bucket name.
      source  = "hashicorp/random"
      version = "~> 3.8"
    }
  }
}
