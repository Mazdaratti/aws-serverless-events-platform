############################################
# Terraform and provider version baseline
############################################

terraform {
  # Keep the example pinned to the same Terraform CLI version line used by the
  # module so local validation stays consistent for anyone testing it.
  required_version = "~> 1.14.0"

  required_providers {
    aws = {
      # Pin the AWS provider to the same stable version line used by the module
      # so the example demonstrates the validated provider baseline.
      source  = "hashicorp/aws"
      version = "~> 6.37"
    }
  }
}
