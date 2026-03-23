
############################################
# Terraform and provider version baseline
############################################
terraform {
  # Keep the environment root pinned to a predictable Terraform CLI version
  # range so local validation stays consistent for everyone working here.
  required_version = "~> 1.14.0"

  required_providers {
    aws = {
      # Pin the AWS provider to a stable minor version line so this environment
      # can be validated consistently as new modules are added over time.
      source  = "hashicorp/aws"
      version = "~> 6.37"
    }
  }
}
