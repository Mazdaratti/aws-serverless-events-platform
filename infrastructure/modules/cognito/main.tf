############################################
# Cognito User Pool
############################################

# Keep the initial User Pool intentionally small but production-shaped so it
# supports the locked identity direction without dragging in later auth features
# such as hosted UI, triggers, or social providers.
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

# This public client is the minimal identity consumer for later frontend and
# API integration. It intentionally avoids OAuth, hosted UI, and secret-based
# flows in this first baseline.
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

# The admin group is created now so later API-layer auth projection has a
# stable identity source for is_admin without needing to reshape Cognito.
resource "aws_cognito_user_group" "admin" {
  user_pool_id = aws_cognito_user_pool.this.id
  name         = var.admin_group_name
  description  = "Administrative group backing future is_admin authorization context."
}
