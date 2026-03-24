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
  # The example builds the same naming pattern used by envs/dev so the module
  # can be tested in isolation without duplicating the full environment root.
  project_name = "aws-serverless-events-platform"
  environment  = "dev"
  name_prefix  = "${local.project_name}-${local.environment}"

  # These baseline tags mirror the current environment convention from envs/dev
  # so the example demonstrates the same tagging shape the real wiring will use.
  tags = {
    Project     = local.project_name
    Environment = local.environment
    ManagedBy   = "Terraform"
  }
}

############################################
# DynamoDB data layer example
############################################

# This example demonstrates the smallest realistic way to call the module.
#
# It intentionally uses the default on-demand billing mode and point-in-time
# recovery settings so the example stays close to the planned dev baseline.
module "dynamodb_data_layer" {
  source = "../../"

  name_prefix = local.name_prefix
  tags        = local.tags
}
