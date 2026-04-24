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

provider "aws" {
  # CloudFront-scoped WAFv2 resources are managed through us-east-1 even when
  # the rest of the dev environment is deployed in the selected regional
  # provider, such as eu-central-1.
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    # Keep global edge resources tagged with the same baseline environment tags
    # as the regional resources created by this root.
    tags = local.tags
  }
}
