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
      # existing modules and environments in this repository.
      source  = "hashicorp/aws"
      version = "~> 6.37"
    }
  }
}
