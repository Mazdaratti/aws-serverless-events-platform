terraform {
  required_version = ">= 1.6.0"
}

############################################
# AWS provider configuration
############################################

provider "aws" {
  # Keep the environment pinned to the operator-selected AWS region so future
  # module wiring stays explicit and easy to reason about.
  region = var.aws_region

  default_tags {
    # Apply the baseline environment tags centrally so future module resources
    # inherit the same metadata without repeating the tag map everywhere.
    tags = local.tags
  }
}
