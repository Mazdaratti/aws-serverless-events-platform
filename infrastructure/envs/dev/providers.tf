############################################
# AWS provider configuration
############################################

provider "aws" {
  # Keep regional resources pinned to the operator-selected AWS region.
  region = var.aws_region

  default_tags {
    # Apply shared environment tags centrally to regional resources.
    tags = local.tags
  }
}

provider "aws" {
  # CloudFront-scoped WAFv2 resources are managed through us-east-1 even when
  # the rest of the dev environment is deployed in the selected regional
  # provider, such as eu-central-1.
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    # Apply the same shared environment tags to global edge resources.
    tags = local.tags
  }
}
