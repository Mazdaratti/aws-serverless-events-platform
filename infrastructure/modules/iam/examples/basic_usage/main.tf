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
  # repository so the IAM module can be validated in a realistic context.
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
# Minimal supporting resources
############################################

# The IAM module generates least-privilege policies from concrete resource
# ARNs, so the example creates a very small set of DynamoDB and SQS resources
# to bind those policies to.
resource "aws_dynamodb_table" "events" {
  name         = "${local.name_prefix}-events"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "event_pk"

  attribute {
    name = "event_pk"
    type = "S"
  }

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-events"
  })
}

resource "aws_dynamodb_table" "rsvps" {
  name         = "${local.name_prefix}-rsvps"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "event_pk"
  range_key    = "subject_sk"

  attribute {
    name = "event_pk"
    type = "S"
  }

  attribute {
    name = "subject_sk"
    type = "S"
  }

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-rsvps"
  })
}

resource "aws_sqs_queue" "notification_dispatch" {
  name = "${local.name_prefix}-notification-dispatch"

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-notification-dispatch"
  })
}

############################################
# IAM module basic usage
############################################

module "iam" {
  source = "../../"

  name_prefix = local.name_prefix
  tags        = local.tags

  events_table_arn                = aws_dynamodb_table.events.arn
  rsvps_table_arn                 = aws_dynamodb_table.rsvps.arn
  notification_dispatch_queue_arn = aws_sqs_queue.notification_dispatch.arn

  workloads = {
    create-event = {
      access_profile = "create_event"
      enable_logs    = true
      enable_xray    = false
    }

    list-events = {
      access_profile = "list_events"
      enable_logs    = true
      enable_xray    = false
    }

    rsvp = {
      access_profile = "rsvp_transaction"
      enable_logs    = true
      enable_xray    = false
    }

    notification-worker = {
      access_profile = "notification_consume"
      enable_logs    = true
      enable_xray    = false
    }
  }
}
