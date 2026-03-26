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
# SQS basic usage example
############################################

# This example demonstrates the smallest realistic way to call the module while
# still covering both supported code paths:
# - one standard queue with a dedicated DLQ
# - one standard queue without a DLQ
module "sqs" {
  source = "../../"

  name_prefix = local.name_prefix
  tags        = local.tags

  queues = {
    async-side-effects = {
      create_dlq                 = true
      visibility_timeout_seconds = 30
      message_retention_seconds  = 345600
      receive_wait_time_seconds  = 0
      max_receive_count          = 5
    }

    # A queue without a DLQ still uses normal queue attributes such as
    # receive_wait_time_seconds = 0. The DLQ-only setting max_receive_count is
    # omitted here because no DLQ is attached to this queue.
    repair-jobs = {
      create_dlq                 = false
      visibility_timeout_seconds = 30
      message_retention_seconds  = 345600
      receive_wait_time_seconds  = 0
    }
  }
}
