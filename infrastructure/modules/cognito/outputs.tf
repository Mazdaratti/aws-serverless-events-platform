############################################
# Cognito identity outputs
############################################

output "user_pool_id" {
  description = "ID of the Cognito User Pool that acts as the platform's managed identity provider."
  value       = aws_cognito_user_pool.this.id
}

output "user_pool_arn" {
  description = "ARN of the Cognito User Pool used by the platform identity model."
  value       = aws_cognito_user_pool.this.arn
}

output "user_pool_client_id" {
  description = "ID of the public Cognito User Pool Client used by API and frontend integrations."
  value       = aws_cognito_user_pool_client.this.id
}

output "issuer" {
  description = "JWT issuer URL derived from the Cognito User Pool for token validation."
  value       = local.issuer
}

output "admin_group_name" {
  description = "Name of the Cognito group used to derive the is_admin caller context."
  value       = aws_cognito_user_group.admin.name
}

output "user_pool_endpoint" {
  description = "Endpoint of the Cognito User Pool for identity integrations and operational reference."
  value       = aws_cognito_user_pool.this.endpoint
}
