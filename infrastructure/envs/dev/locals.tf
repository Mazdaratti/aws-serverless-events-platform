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
}
