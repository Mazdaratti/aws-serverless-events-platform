############################################
# Example provider and shared context
############################################

provider "aws" {
  # CloudFront-scoped WAFv2 resources must be managed through us-east-1, even
  # when the rest of the platform is deployed in another AWS region.
  alias  = "us_east_1"
  region = "us-east-1"
}

locals {
  # Keep the example self-contained by defining a small naming and tagging
  # baseline here instead of depending on any environment root.
  name_prefix = "example-events-platform"

  tags = {
    Project     = "aws-serverless-events-platform"
    Environment = "example"
    ManagedBy   = "Terraform"
  }
}

############################################
# WAF basic usage
############################################

# This example demonstrates a CloudFront-scoped WAFv2 Web ACL intended for
# association with a public edge distribution.
module "waf" {
  source = "../../"

  providers = {
    aws = aws.us_east_1
  }

  name_prefix = local.name_prefix
  tags        = local.tags

  web_acl_name_suffix = "edge"
  rate_limit_enabled  = true
  rate_limit          = 2000
}
