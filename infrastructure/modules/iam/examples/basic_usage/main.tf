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
# ARNs, so the example creates a very small set of DynamoDB, SQS, and Cognito
# resources to bind those policies to.
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

resource "aws_sqs_queue" "notification_email" {
  name = "${local.name_prefix}-notification-email"

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-notification-email"
  })
}

resource "aws_cognito_user_pool" "users" {
  name = "${local.name_prefix}-users"

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-users"
  })
}

# The IAM module can optionally grant write workloads permission to publish
# compact domain events. This example creates a small custom bus so that
# permission can be scoped to a concrete EventBridge resource.
resource "aws_cloudwatch_event_bus" "domain_events" {
  name = "${local.name_prefix}-events"

  tags = merge(local.tags, {
    Name = "${local.name_prefix}-events"
  })
}

############################################
# IAM module basic usage
############################################

module "iam" {
  source = "../../"

  name_prefix = local.name_prefix
  tags        = local.tags

  events_table_arn                  = aws_dynamodb_table.events.arn
  rsvps_table_arn                   = aws_dynamodb_table.rsvps.arn
  notification_dispatch_queue_arn   = aws_sqs_queue.notification_dispatch.arn
  notification_email_queue_arn      = aws_sqs_queue.notification_email.arn
  cognito_user_pool_arn             = aws_cognito_user_pool.users.arn
  eventbridge_publish_event_bus_arn = aws_cloudwatch_event_bus.domain_events.arn

  workloads = {
    create-event = {
      access_profile = "create_event"
      enable_logs    = true
      enable_xray    = false
    }

    get-event = {
      access_profile = "get_event"
      enable_logs    = true
      enable_xray    = false
    }

    list-events = {
      access_profile = "list_events"
      enable_logs    = true
      enable_xray    = false
    }

    list-my-events = {
      access_profile = "list_my_events"
      enable_logs    = true
      enable_xray    = false
    }

    update-event = {
      access_profile = "update_event"
      enable_logs    = true
      enable_xray    = false
    }

    cancel-event = {
      access_profile = "cancel_event"
      enable_logs    = true
      enable_xray    = false
    }

    # The dedicated mixed-mode Lambda authorizer validates caller identity
    # only, so the example uses the logs-only authorizer profile.
    rsvp-authorizer = {
      access_profile = "authorizer_logs_only"
      enable_logs    = true
      enable_xray    = false
    }

    rsvp = {
      access_profile = "rsvp_transaction"
      enable_logs    = true
      enable_xray    = false
    }

    # This workload reads the canonical event first and then queries one RSVP
    # page, so the example includes the matching read-only access profile.
    get-event-rsvps = {
      access_profile = "get_event_rsvps"
      enable_logs    = true
      enable_xray    = false
    }

    notification-planner = {
      access_profile = "notification_planner"
      enable_logs    = true
      enable_xray    = false
    }

    notification-sender = {
      access_profile = "notification_sender"
      enable_logs    = true
      enable_xray    = false
    }
  }
}
