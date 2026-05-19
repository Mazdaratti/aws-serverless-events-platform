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
  # repository so the observability module can be validated in a realistic
  # context.
  project_name = "aws-serverless-events-platform"
  environment  = "example"
  name_prefix  = "${local.project_name}-${local.environment}"

  tags = {
    Project     = local.project_name
    Environment = local.environment
    ManagedBy   = "Terraform"
  }
}

############################################
# Observability module basic usage
############################################

# This example is runnable and creates CloudWatch metric alarms only. It uses
# documentation-safe example metric dimensions instead of creating a full
# Lambda/API/SQS/EventBridge stack, because this module owns observability
# resources rather than runtime workloads.
#
# The alarms can be applied as-is, but they will only receive live metric data
# if matching workloads exist and emit the corresponding AWS service metrics.
module "observability" {
  source = "../../"

  name_prefix = local.name_prefix
  tags        = local.tags

  alarm_actions = []
  ok_actions    = []

  dashboard_enabled = true

  lambda_functions = {
    create_event        = "${local.name_prefix}-create-event"
    notification_sender = "${local.name_prefix}-notification-sender"
  }

  api_gateway_api_id     = "abc123example"
  api_gateway_stage_name = local.environment

  sqs_queue_names = {
    notification_dispatch = "${local.name_prefix}-notification-dispatch"
    notification_email    = "${local.name_prefix}-notification-email"
  }

  sqs_dlq_names = {
    notification_dispatch = "${local.name_prefix}-notification-dispatch-dlq"
    notification_email    = "${local.name_prefix}-notification-email-dlq"
  }

  eventbridge_bus_name = "${local.name_prefix}-events"

  eventbridge_rule_names = {
    participant_notification_dispatch = "${local.name_prefix}-participant-notification-dispatch"
    admin_lifecycle_notifications     = "${local.name_prefix}-admin-lifecycle-notifications"
  }
}
