############################################
# Example verification outputs
############################################

output "user_pool_id" {
  description = "Rendered Cognito User Pool ID created by the basic_usage example."
  value       = module.cognito.user_pool_id
}

output "user_pool_client_id" {
  description = "Rendered Cognito User Pool Client ID created by the basic_usage example."
  value       = module.cognito.user_pool_client_id
}

output "issuer" {
  description = "Rendered JWT issuer URL created by the basic_usage example."
  value       = module.cognito.issuer
}

output "admin_group_name" {
  description = "Rendered Cognito admin group name created by the basic_usage example."
  value       = module.cognito.admin_group_name
}

output "user_pool_endpoint" {
  description = "Rendered Cognito User Pool endpoint created by the basic_usage example."
  value       = module.cognito.user_pool_endpoint
}
