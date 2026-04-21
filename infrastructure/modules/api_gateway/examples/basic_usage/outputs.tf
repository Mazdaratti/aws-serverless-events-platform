############################################
# Example outputs
############################################

output "api_id" {
  description = "ID of the example HTTP API."
  value       = module.api_gateway.api_id
}

output "api_endpoint" {
  description = "Base invoke endpoint of the example HTTP API."
  value       = module.api_gateway.api_endpoint
}

output "stage_invoke_url" {
  description = "Stage-qualified invoke URL of the example HTTP API."
  value       = module.api_gateway.stage_invoke_url
}

output "jwt_authorizer_id" {
  description = "JWT authorizer ID created by the example."
  value       = module.api_gateway.jwt_authorizer_id
}

output "request_authorizer_ids" {
  description = "Map of logical request authorizer key to HTTP API authorizer ID for the example."
  value       = module.api_gateway.request_authorizer_ids
}

output "route_keys" {
  description = "Map of logical route name to route key created by the example."
  value       = module.api_gateway.route_keys
}

output "api_access_log_group_name" {
  description = "CloudWatch Logs log group name used by the example for API Gateway access logging."
  value       = aws_cloudwatch_log_group.api_access.name
}
