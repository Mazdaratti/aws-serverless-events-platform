############################################
# HTTP API outputs
############################################

output "api_id" {
  description = "ID of the HTTP API created by the module."
  value       = aws_apigatewayv2_api.this.id
}

output "api_arn" {
  description = "ARN of the HTTP API created by the module."
  value       = aws_apigatewayv2_api.this.arn
}

output "api_execution_arn" {
  description = "Execution ARN of the HTTP API created by the module."
  value       = aws_apigatewayv2_api.this.execution_arn
}

output "api_endpoint" {
  description = "Base invoke endpoint of the HTTP API created by the module."
  value       = aws_apigatewayv2_api.this.api_endpoint
}

############################################
# Stage outputs
############################################

output "stage_name" {
  description = "Stage name created by the module."
  value       = aws_apigatewayv2_stage.this.name
}

output "stage_invoke_url" {
  description = "Stage-qualified invoke URL for the HTTP API created by the module."
  value       = "${aws_apigatewayv2_api.this.api_endpoint}/${aws_apigatewayv2_stage.this.name}"
}

############################################
# Authorizer outputs
############################################

output "jwt_authorizer_id" {
  description = "ID of the JWT authorizer created by the module."
  value       = aws_apigatewayv2_authorizer.jwt.id
}

############################################
# Route outputs
############################################

output "route_ids" {
  description = "Map of logical route name to HTTP API route ID created by the module."
  value = {
    for route_name, route in aws_apigatewayv2_route.route :
    route_name => route.id
  }
}

output "route_keys" {
  description = "Map of logical route name to HTTP API route key created by the module."
  value = {
    for route_name, route in aws_apigatewayv2_route.route :
    route_name => route.route_key
  }
}
