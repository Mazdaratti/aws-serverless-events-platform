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
# Example target resource
############################################

# The EventBridge module owns the bus, rules, and targets. This queue exists
# only so the example has a concrete target ARN to pass into the module.
resource "aws_sqs_queue" "participant_dispatch" {
  name = "${local.name_prefix}-example-participant-dispatch"

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-example-participant-dispatch"
  })
}

############################################
# EventBridge basic usage example
############################################

# This example demonstrates the platform-ready EventBridge module shape:
# - one custom event bus
# - one rule using a structured event pattern
# - one target attached to that rule
module "eventbridge" {
  source = "../../"

  name_prefix = local.name_prefix
  tags        = local.tags

  rules = {
    participant_notification_dispatch = {
      description = "Route participant notification planning events to SQS."

      event_pattern = {
        source        = ["aws-serverless-events-platform"]
        "detail-type" = ["event.updated", "event.cancelled"]
      }

      targets = {
        dispatch_queue = {
          arn = aws_sqs_queue.participant_dispatch.arn
        }
      }
    }
  }
}

############################################
# Example target resource policy
############################################

# EventBridge target permissions belong outside the EventBridge module because
# they protect the target resource. Since this example owns the SQS queue, it
# also owns the queue policy that allows the EventBridge rule to send messages.
data "aws_iam_policy_document" "participant_dispatch_eventbridge_send" {
  statement {
    sid    = "AllowEventBridgeParticipantDispatch"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }

    actions = [
      "sqs:SendMessage",
    ]

    resources = [
      aws_sqs_queue.participant_dispatch.arn,
    ]

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values = [
        module.eventbridge.rule_arns["participant_notification_dispatch"],
      ]
    }
  }
}

resource "aws_sqs_queue_policy" "participant_dispatch" {
  queue_url = aws_sqs_queue.participant_dispatch.id
  policy    = data.aws_iam_policy_document.participant_dispatch_eventbridge_send.json
}
