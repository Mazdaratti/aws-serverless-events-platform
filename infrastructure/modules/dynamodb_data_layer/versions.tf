############################################
# Terraform and provider version baseline
############################################

terraform {
  # Keep the module pinned to the same Terraform CLI version line used by the
  # environment root so validation stays consistent across the repository.
  required_version = "~> 1.14.0"

  required_providers {
    aws = {
      # Pin the AWS provider to the same stable version line used in envs/dev
      # so module behavior is validated against the same provider baseline.
      source  = "hashicorp/aws"
      version = "~> 6.37"
    }
  }
}
