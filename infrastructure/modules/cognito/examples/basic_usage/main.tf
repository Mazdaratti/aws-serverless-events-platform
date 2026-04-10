############################################
# Example provider and shared context
############################################

provider "aws" {
  # This example configures the AWS provider inline so a beginner can run it
  # without needing extra files beyond the minimal example set.
  #
  # The region should match the region configured in envs/dev.
  region = "eu-central-1"
}

locals {
  # The example keeps the same naming and tagging shape used elsewhere in the
  # repository so the Cognito module can be validated in a realistic context.
  project_name = "aws-serverless-events-platform"
  environment  = "dev"
  name_prefix  = "${local.project_name}-${local.environment}"

  tags = {
    Project     = local.project_name
    Environment = local.environment
    ManagedBy   = "Terraform"
  }
}

############################################
# Cognito module basic usage
############################################

module "cognito" {
  source = "../../"

  name_prefix = local.name_prefix
  tags        = local.tags

  allow_self_signup           = true
  require_email               = true
  deletion_protection_enabled = false
}
