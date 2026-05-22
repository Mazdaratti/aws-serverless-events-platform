############################################
# AWS provider configuration
############################################

provider "aws" {
  # Bootstrap resources for the dev backend and GitHub OIDC role are created
  # in the operator-selected AWS region.
  region = var.aws_region

  default_tags {
    tags = local.tags
  }
}
