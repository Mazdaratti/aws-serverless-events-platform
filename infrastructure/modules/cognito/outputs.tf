############################################
# Cognito identity baseline outputs
############################################

output "user_pool_id" {
  description = "ID of the Cognito User Pool that acts as the platform's managed identity provider."
  value       = aws_cognito_user_pool.this.id
}

output "user_pool_arn" {
  description = "ARN of the Cognito User Pool used by the platform identity baseline."
  value       = aws_cognito_user_pool.this.arn
}

output "user_pool_client_id" {
  description = "ID of the public Cognito User Pool Client that later API and frontend layers can use."
  value       = aws_cognito_user_pool_client.this.id
}

output "issuer" {
  description = "JWT issuer URL derived from the Cognito User Pool for later API Gateway JWT validation wiring."
  value       = local.issuer
}

output "admin_group_name" {
  description = "Name of the Cognito group that backs the future is_admin caller-context projection."
  value       = aws_cognito_user_group.admin.name
}

output "user_pool_endpoint" {
  description = "Endpoint of the Cognito User Pool. This is optional but can be useful for later integration and documentation."
  value       = aws_cognito_user_pool.this.endpoint
}
