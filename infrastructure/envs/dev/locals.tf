############################################
# Derived naming and tagging values
############################################

locals {
  # Standard prefix for resources created in this environment.
  #
  # Example:
  # aws-serverless-events-platform-dev
  name_prefix = "${var.project_name}-${var.environment}"

  # Baseline tags applied consistently by future module blocks in this
  # environment so shared metadata does not need to be repeated everywhere.
  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }

  # The EventBridge bus name follows the same convention the reusable module
  # derives by default. Keeping the name and ARN available as env-level locals
  # lets IAM and Lambda wiring use deterministic values without depending on
  # module.eventbridge outputs. That keeps the dependency graph acyclic when
  # EventBridge target formatting references CloudFront.
  eventbridge_event_bus_name = "${local.name_prefix}-events"
  eventbridge_event_bus_arn  = "arn:${data.aws_partition.current.partition}:events:${var.aws_region}:${data.aws_caller_identity.current.account_id}:event-bus/${local.eventbridge_event_bus_name}"

  # Keep Lambda deployment inputs thinner in main.tf by defining only the
  # workload-specific values here. Shared deployment defaults can then be
  # derived centrally when the Lambda module is called.
  lambda_workloads = {
    create-event = {
      description = "Creates a new event record in the canonical events table."
    }

    get-event = {
      description = "Reads a single canonical event record by public identifier."
    }

    list-events = {
      description = "Lists public events from the canonical events table using the current temporary broad scan path."
    }

    list-my-events = {
      description = "Lists creator-scoped events from the canonical events table through the creator-events GSI."
    }

    update-event = {
      description = "Performs partial updates on a canonical event record while preserving ownership and index rules."
    }

    cancel-event = {
      description = "Soft-deletes a canonical event record by setting status to CANCELLED and removing public discovery helpers."
    }

    rsvp-authorizer = {
      description = "Validates mixed-mode RSVP caller identity and projects a flat authorizer context for downstream Lambda use."
    }

    rsvp = {
      description = "Writes transactional RSVP state for one event and subject while keeping helper counters correct."
    }

    get-event-rsvps = {
      description = "Reads one event's RSVP list for the creator or an admin using the canonical event-first authorization flow."
    }
  }

  # Notification workers are deployed in a later Lambda module call so sender
  # environment variables can use the CloudFront distribution domain without
  # creating a Lambda -> API Gateway -> CloudFront -> Lambda dependency cycle.
  notification_lambda_workloads = {
    notification-planner = {
      description = "Consumes event-level participant notification planning messages and enqueues recipient-level email jobs."
    }

    notification-sender = {
      description = "Consumes recipient-level participant email jobs and sends templated emails through SES."
    }
  }
}
