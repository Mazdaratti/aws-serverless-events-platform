############################################
# Environment composition root
############################################

# This root module stays intentionally small.
#
# It currently establishes the shared environment baseline only:
# - Terraform and provider version constraints
# - AWS provider configuration
# - environment naming and tagging context
#
# Reusable AWS resources will be added later through module blocks as the
# platform is implemented step by step.
locals {
  _environment_context_ready = local.name_prefix
}
