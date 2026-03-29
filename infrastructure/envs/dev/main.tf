############################################
# Environment composition root
############################################

# This root module stays intentionally small.
#
# It establishes the shared environment baseline and composes reusable
# infrastructure modules for the dev environment.
#
# The root keeps only environment-level concerns:
# - Terraform and provider version constraints
# - AWS provider configuration
# - environment naming and tagging context
# - module composition
#
# Reusable AWS resource design stays inside modules so envs/dev remains thin
# and composition-focused as the platform is implemented step by step.

############################################
# DynamoDB business data layer
############################################

# This environment wires in the first reusable business data module for the
# platform. The module owns the DynamoDB table design so envs/dev can stay
# focused on composition and environment-level context only.
module "dynamodb_data_layer" {
  source = "../../modules/dynamodb_data_layer"

  name_prefix = local.name_prefix
  tags        = local.tags
}

############################################
# SQS messaging baseline
############################################

# This environment wires in the first reusable messaging module for the
# platform. The queue is intended for durable post-commit notification work,
# while the synchronous RSVP write path remains outside SQS.
#
# The module owns the queue and DLQ design so envs/dev can stay focused on
# composition and environment-level context only.
module "sqs" {
  source = "../../modules/sqs"

  name_prefix = local.name_prefix
  tags        = local.tags

  queues = {
    notification-dispatch = {
      create_dlq                 = true
      visibility_timeout_seconds = 30
      message_retention_seconds  = 345600
      receive_wait_time_seconds  = 0
      max_receive_count          = 5
    }
  }
}
