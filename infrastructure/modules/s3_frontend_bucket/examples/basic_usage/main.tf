############################################
# Basic example configuration
############################################

provider "aws" {
  region = "eu-central-1"
}

locals {
  # Keep the example self-contained by defining a small naming and tagging
  # baseline here instead of depending on any environment root.
  name_prefix = "example-events-platform"

  tags = {
    Project     = "aws-serverless-events-platform"
    Environment = "example"
    ManagedBy   = "Terraform"
  }
}

module "s3_frontend_bucket" {
  source = "../../"

  # This example demonstrates the intended baseline for a private S3 bucket
  # that will later sit behind CloudFront as a frontend origin.
  name_prefix        = local.name_prefix
  bucket_name_suffix = "frontend"
  tags               = local.tags
  versioning_enabled = true
  force_destroy      = false
}
