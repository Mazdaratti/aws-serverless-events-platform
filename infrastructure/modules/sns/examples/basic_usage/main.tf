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
# SNS basic usage example
############################################

# This example creates the admin notification topic without email subscriptions.
# That keeps the example safe to run because SNS email subscriptions send
# confirmation messages to the configured recipients.
#
# Real environment wiring can pass confirmed admin or developer email endpoints
# through email_subscriptions without hardcoding personal addresses in reusable
# module code.
module "sns" {
  source = "../../"

  name_prefix         = local.name_prefix
  tags                = local.tags
  email_subscriptions = []
}
