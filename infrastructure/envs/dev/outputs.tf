############################################
# DynamoDB data layer outputs
############################################

# ******************************************
# Events table
# ******************************************

output "events_table_name" {
  description = "Name of the DynamoDB events table created for the dev environment."
  value       = module.dynamodb_data_layer.events_table_name
}

output "events_table_arn" {
  description = "ARN of the DynamoDB events table created for the dev environment."
  value       = module.dynamodb_data_layer.events_table_arn
}

# ******************************************
# RSVPs table
# ******************************************

output "rsvps_table_name" {
  description = "Name of the DynamoDB RSVP table created for the dev environment."
  value       = module.dynamodb_data_layer.rsvps_table_name
}

output "rsvps_table_arn" {
  description = "ARN of the DynamoDB RSVP table created for the dev environment."
  value       = module.dynamodb_data_layer.rsvps_table_arn
}

############################################
# SQS messaging baseline outputs
############################################

# These outputs re-export the generic queue maps from the SQS module so later
# environment-level consumers can look up the currently wired queue identities
# by logical queue key.
output "sqs_queue_names" {
  description = "Map of logical queue key to rendered SQS queue name for the dev environment."
  value       = module.sqs.queue_names
}

output "sqs_queue_arns" {
  description = "Map of logical queue key to rendered SQS queue ARN for the dev environment."
  value       = module.sqs.queue_arns
}

output "sqs_queue_urls" {
  description = "Map of logical queue key to rendered SQS queue URL for the dev environment."
  value       = module.sqs.queue_urls
}

output "sqs_dlq_names" {
  description = "Map of logical queue key to rendered SQS DLQ name for queues that create a dedicated DLQ in the dev environment."
  value       = module.sqs.dlq_names
}

output "sqs_dlq_arns" {
  description = "Map of logical queue key to rendered SQS DLQ ARN for queues that create a dedicated DLQ in the dev environment."
  value       = module.sqs.dlq_arns
}

output "sqs_dlq_urls" {
  description = "Map of logical queue key to rendered SQS DLQ URL for queues that create a dedicated DLQ in the dev environment."
  value       = module.sqs.dlq_urls
}

############################################
# Lambda execution IAM baseline outputs
############################################

# These outputs re-export the workload-keyed IAM role maps from the IAM module
# so later environment-level consumers can bind Lambda functions to the correct
# execution roles without re-describing IAM policy internals here.
output "iam_role_names" {
  description = "Map of workload IAM role names for the dev environment."
  value       = module.iam.role_names
}

output "iam_role_arns" {
  description = "Map of workload IAM role ARNs for the dev environment."
  value       = module.iam.role_arns
}

############################################
# Lambda compute baseline outputs
############################################

# These outputs re-export the workload-keyed Lambda maps from the Lambda module
# so later environment-level consumers can integrate the deployed functions
# without re-describing Lambda infrastructure internals here.
output "lambda_function_names" {
  description = "Map of workload Lambda function names for the dev environment."
  value       = module.lambda.function_names
}

output "lambda_function_arns" {
  description = "Map of workload Lambda function ARNs for the dev environment."
  value       = module.lambda.function_arns
}

output "lambda_invoke_arns" {
  description = "Map of workload Lambda invoke ARNs for the dev environment."
  value       = module.lambda.invoke_arns
}

output "lambda_log_group_names" {
  description = "Map of workload CloudWatch Logs log group names for the dev environment."
  value       = module.lambda.log_group_names
}

output "lambda_log_group_arns" {
  description = "Map of workload CloudWatch Logs log group ARNs for the dev environment."
  value       = module.lambda.log_group_arns
}

############################################
# Cognito identity baseline outputs
############################################

# These outputs re-export the key Cognito identities from the module so later
# environment-level consumers such as API Gateway wiring can use them directly
# without re-describing Cognito internals in the root.
output "cognito_user_pool_id" {
  description = "ID of the Cognito User Pool created for the dev environment."
  value       = module.cognito.user_pool_id
}

output "cognito_user_pool_arn" {
  description = "ARN of the Cognito User Pool created for the dev environment."
  value       = module.cognito.user_pool_arn
}

output "cognito_user_pool_client_id" {
  description = "ID of the Cognito User Pool Client created for the dev environment."
  value       = module.cognito.user_pool_client_id
}

output "cognito_issuer" {
  description = "JWT issuer URL for the Cognito User Pool created for the dev environment."
  value       = module.cognito.issuer
}

output "cognito_admin_group_name" {
  description = "Name of the Cognito admin group created for the dev environment."
  value       = module.cognito.admin_group_name
}

output "cognito_user_pool_endpoint" {
  description = "Endpoint of the Cognito User Pool created for the dev environment."
  value       = module.cognito.user_pool_endpoint
}

############################################
# API Gateway routed backend baseline outputs
############################################

# These outputs expose the current routed backend baseline so the environment
# can be tested end to end without requiring callers to inspect the
# api_gateway module internals directly.
output "api_gateway_api_id" {
  description = "ID of the HTTP API created for the dev environment routed backend baseline."
  value       = module.api_gateway.api_id
}

output "api_gateway_api_arn" {
  description = "ARN of the HTTP API created for the dev environment routed backend baseline."
  value       = module.api_gateway.api_arn
}

output "api_gateway_execution_arn" {
  description = "Execution ARN of the HTTP API created for the dev environment routed backend baseline."
  value       = module.api_gateway.api_execution_arn
}

output "api_gateway_api_endpoint" {
  description = "Base invoke endpoint of the HTTP API created for the dev environment routed backend baseline."
  value       = module.api_gateway.api_endpoint
}

output "api_gateway_stage_name" {
  description = "Stage name of the HTTP API created for the dev environment routed backend baseline."
  value       = module.api_gateway.stage_name
}

output "api_gateway_stage_invoke_url" {
  description = "Stage-qualified invoke URL of the HTTP API created for the dev environment routed backend baseline."
  value       = module.api_gateway.stage_invoke_url
}

output "api_gateway_jwt_authorizer_id" {
  description = "JWT authorizer ID of the HTTP API created for the dev environment routed backend baseline."
  value       = module.api_gateway.jwt_authorizer_id
}

output "api_gateway_request_authorizer_ids" {
  description = "Map of logical Lambda request authorizer name to HTTP API authorizer ID for the dev environment routed backend baseline."
  value       = module.api_gateway.request_authorizer_ids
}

output "api_gateway_route_ids" {
  description = "Map of logical route name to route ID for the dev environment routed backend baseline."
  value       = module.api_gateway.route_ids
}

output "api_gateway_route_keys" {
  description = "Map of logical route name to route key for the dev environment routed backend baseline."
  value       = module.api_gateway.route_keys
}
