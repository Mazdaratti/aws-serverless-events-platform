############################################
# Normalized Cognito configuration
############################################

data "aws_region" "current" {}

locals {
  # Render stable Cognito names from the shared prefix unless the caller
  # explicitly overrides them.
  user_pool_name = coalesce(
    var.user_pool_name_override,
    "${var.name_prefix}-users"
  )

  user_pool_client_name = coalesce(
    var.user_pool_client_name_override,
    "${var.name_prefix}-app-client"
  )

  # Keep the standard attribute surface intentionally small in v1 so the
  # module matches the locked identity baseline without speculative fields.
  required_standard_attributes = var.require_email ? ["email"] : []

  # Expose a simple boolean input while still rendering the AWS-specific
  # deletion protection enum expected by Cognito.
  cognito_deletion_protection = var.deletion_protection_enabled ? "ACTIVE" : "INACTIVE"

  # Pre-render the JWT issuer value that later API Gateway integration will
  # need, so the output stays easy to consume from env roots.
  issuer = "https://cognito-idp.${data.aws_region.current.region}.amazonaws.com/${aws_cognito_user_pool.this.id}"
}
