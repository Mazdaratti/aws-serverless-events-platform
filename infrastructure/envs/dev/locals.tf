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
      description = "Lists events from the canonical events table using the current platform query modes."
    }

    update-event = {
      description = "Performs partial updates on a canonical event record while preserving ownership and index rules."
    }
  }
}
