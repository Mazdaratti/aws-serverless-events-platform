############################################
# Provider configuration
############################################

provider "aws" {
  region = "eu-central-1"
}

############################################
# Basic remote backend example
############################################

module "remote_backend" {
  source = "../.."

  # This example lets the module derive a globally unique bucket name from the
  # prefix plus a random suffix. It is runnable, but creates real AWS resources
  # if applied.
  name_prefix = "aws-serverless-events-platform-example"

  tags = {
    Project     = "aws-serverless-events-platform"
    Environment = "example"
    ManagedBy   = "Terraform"
    Module      = "remote_backend"
  }
}
