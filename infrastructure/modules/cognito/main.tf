############################################
# Cognito User Pool
############################################

# Keep the User Pool focused on the platform's identity contract without adding
# hosted UI, triggers, or social identity providers.
resource "aws_cognito_user_pool" "this" {
  name = local.user_pool_name

  deletion_protection = local.cognito_deletion_protection

  username_configuration {
    case_sensitive = var.username_case_sensitive
  }

  auto_verified_attributes = local.required_standard_attributes

  admin_create_user_config {
    allow_admin_create_user_only = !var.allow_self_signup
  }

  password_policy {
    minimum_length                   = var.password_minimum_length
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = false
    temporary_password_validity_days = 7
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  dynamic "schema" {
    for_each = var.require_email ? [1] : []

    content {
      attribute_data_type = "String"
      name                = "email"
      required            = true
      mutable             = true
    }
  }

  tags = merge(var.tags, {
    Name = local.user_pool_name
  })
}

############################################
# Cognito User Pool Client
############################################

# This public client supports frontend authentication and API token validation.
# It intentionally avoids OAuth, hosted UI, and secret-based flows.
resource "aws_cognito_user_pool_client" "this" {
  name         = local.user_pool_client_name
  user_pool_id = aws_cognito_user_pool.this.id

  generate_secret               = false
  enable_token_revocation       = true
  prevent_user_existence_errors = "ENABLED"

  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH"
  ]

  supported_identity_providers = ["COGNITO"]
}

############################################
# Cognito admin group
############################################

# The admin group provides the stable membership source used to derive the
# is_admin caller context.
resource "aws_cognito_user_group" "admin" {
  user_pool_id = aws_cognito_user_pool.this.id
  name         = var.admin_group_name
  description  = "Administrative group used to derive the is_admin authorization context."
}
