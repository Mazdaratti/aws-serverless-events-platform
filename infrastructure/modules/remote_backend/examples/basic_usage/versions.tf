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
      # The module uses random_id to derive a globally unique bucket name when
      # the caller does not pass an explicit state_bucket_name.
      source  = "hashicorp/random"
      version = "~> 3.8"
    }
  }
}
