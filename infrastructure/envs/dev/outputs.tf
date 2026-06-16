############################################
# Environment deployment context outputs
############################################

# Frontend deployment helpers need the selected regional AWS provider context
# so they can build public Vite config and run regional S3 commands without
# hardcoding an environment-specific value outside Terraform.
output "aws_region" {
  description = "AWS region selected for regional resources in the dev environment."
  value       = var.aws_region
}

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
# SQS messaging outputs
############################################

# These outputs expose queue identities by logical queue key without requiring
# consumers to inspect the SQS module internals.
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
# EventBridge event bus outputs
############################################

# These outputs expose the custom EventBridge bus identity for routing,
# permissions, validation, and operational inspection.
output "eventbridge_event_bus_name" {
  description = "Name of the custom EventBridge event bus created for the dev environment."
  value       = module.eventbridge.event_bus_name
}

output "eventbridge_event_bus_arn" {
  description = "ARN of the custom EventBridge event bus created for the dev environment."
  value       = module.eventbridge.event_bus_arn
}

output "eventbridge_event_bus_id" {
  description = "ID of the custom EventBridge event bus created for the dev environment."
  value       = module.eventbridge.event_bus_id
}

# These outputs expose EventBridge rule and target identities by logical key.
output "eventbridge_rule_names" {
  description = "Map of logical EventBridge rule key to rendered rule name for the dev environment."
  value       = module.eventbridge.rule_names
}

output "eventbridge_rule_arns" {
  description = "Map of logical EventBridge rule key to rendered rule ARN for the dev environment."
  value       = module.eventbridge.rule_arns
}

output "eventbridge_target_ids" {
  description = "Map of logical EventBridge target key in rule.target form to target ID for the dev environment."
  value       = module.eventbridge.target_ids
}

output "eventbridge_target_arns" {
  description = "Map of logical EventBridge target key in rule.target form to target ARN for the dev environment."
  value       = module.eventbridge.target_arns
}

############################################
# SNS admin notification outputs
############################################

# These outputs expose the admin notification topic and subscription identities.
output "sns_admin_topic_name" {
  description = "Name of the SNS admin notification topic created for the dev environment."
  value       = module.sns_admin_notifications.topic_name
}

output "sns_admin_topic_arn" {
  description = "ARN of the SNS admin notification topic created for the dev environment."
  value       = module.sns_admin_notifications.topic_arn
}

output "sns_admin_topic_id" {
  description = "ID of the SNS admin notification topic created for the dev environment."
  value       = module.sns_admin_notifications.topic_id
}

output "sns_admin_email_subscription_arns" {
  description = "Map of admin email endpoint to SNS subscription ARN for the dev environment."
  value       = module.sns_admin_notifications.email_subscription_arns
}

############################################
# SES participant email outputs
############################################

output "ses_sender_identity_arn" {
  description = "ARN of the SES sender email identity configured for participant notifications in dev."
  value       = module.ses_participant_email.sender_identity_arn
}

output "ses_template_names" {
  description = "Map of participant notification type to SES template name for dev."
  value       = module.ses_participant_email.template_names
}

output "ses_template_arns" {
  description = "Map of participant notification type to SES template ARN for dev."
  value       = module.ses_participant_email.template_arns
}

############################################
# Lambda execution IAM outputs
############################################

# These outputs expose workload-keyed IAM role identities without re-describing
# IAM policy internals.
output "iam_role_names" {
  description = "Map of workload IAM role names for the dev environment."
  value       = module.iam.role_names
}

output "iam_role_arns" {
  description = "Map of workload IAM role ARNs for the dev environment."
  value       = module.iam.role_arns
}

############################################
# Lambda compute outputs
############################################

# These outputs combine workload-keyed Lambda identities from both module calls
# for deployment and environment integrations.
output "lambda_function_names" {
  description = "Map of workload Lambda function names for the dev environment."
  value = merge(
    module.lambda.function_names,
    module.notification_lambdas.function_names,
  )
}

output "lambda_function_arns" {
  description = "Map of workload Lambda function ARNs for the dev environment."
  value = merge(
    module.lambda.function_arns,
    module.notification_lambdas.function_arns,
  )
}

output "lambda_invoke_arns" {
  description = "Map of workload Lambda invoke ARNs for the dev environment."
  value = merge(
    module.lambda.invoke_arns,
    module.notification_lambdas.invoke_arns,
  )
}

output "lambda_log_group_names" {
  description = "Map of workload CloudWatch Logs log group names for the dev environment."
  value = merge(
    module.lambda.log_group_names,
    module.notification_lambdas.log_group_names,
  )
}

output "lambda_log_group_arns" {
  description = "Map of workload CloudWatch Logs log group ARNs for the dev environment."
  value = merge(
    module.lambda.log_group_arns,
    module.notification_lambdas.log_group_arns,
  )
}

############################################
# Cognito identity outputs
############################################

# These outputs expose Cognito identities used by API authorization, frontend
# authentication, and operational tooling.
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
# S3 frontend origin outputs
############################################

# These outputs expose the private frontend origin bucket values used by edge
# delivery and frontend deployment tooling.
output "frontend_bucket_arn" {
  description = "ARN of the private frontend origin bucket created for the dev environment."
  value       = module.s3_frontend_bucket.bucket_arn
}

output "frontend_bucket_id" {
  description = "ID of the private frontend origin bucket created for the dev environment."
  value       = module.s3_frontend_bucket.bucket_id
}

output "frontend_bucket_name" {
  description = "Name of the private frontend origin bucket created for the dev environment."
  value       = module.s3_frontend_bucket.bucket_name
}

output "frontend_bucket_regional_domain_name" {
  description = "Regional domain name of the private frontend origin bucket created for the dev environment."
  value       = module.s3_frontend_bucket.bucket_regional_domain_name
}

############################################
# WAF edge protection outputs
############################################

# These outputs expose the CloudFront-scoped Web ACL values when WAF is enabled
# in dev. They return null when WAF is disabled for cost-aware operation.
output "waf_web_acl_arn" {
  description = "ARN of the CloudFront-scoped Web ACL created for the dev environment, or null when WAF is disabled."
  value       = var.enable_waf ? module.waf[0].web_acl_arn : null
}

output "waf_web_acl_id" {
  description = "ID of the CloudFront-scoped Web ACL created for the dev environment, or null when WAF is disabled."
  value       = var.enable_waf ? module.waf[0].web_acl_id : null
}

output "waf_web_acl_name" {
  description = "Name of the CloudFront-scoped Web ACL created for the dev environment, or null when WAF is disabled."
  value       = var.enable_waf ? module.waf[0].web_acl_name : null
}

############################################
# CloudFront edge distribution outputs
############################################

# These outputs expose CloudFront distribution values used by browser
# validation, frontend deployment, and optional DNS or custom-domain
# integrations.
output "cloudfront_distribution_id" {
  description = "ID of the CloudFront distribution created for the dev environment."
  value       = module.cloudfront.distribution_id
}

output "cloudfront_distribution_arn" {
  description = "ARN of the CloudFront distribution created for the dev environment."
  value       = module.cloudfront.distribution_arn
}

output "cloudfront_distribution_domain_name" {
  description = "Domain name of the CloudFront distribution created for the dev environment."
  value       = module.cloudfront.distribution_domain_name
}

output "cloudfront_distribution_hosted_zone_id" {
  description = "Route 53 hosted zone ID used by the CloudFront distribution created for the dev environment."
  value       = module.cloudfront.distribution_hosted_zone_id
}

output "cloudfront_s3_origin_access_control_id" {
  description = "ID of the Origin Access Control used by the dev CloudFront distribution for the private S3 frontend origin."
  value       = module.cloudfront.s3_origin_access_control_id
}

output "cloudfront_spa_rewrite_function_arn" {
  description = "ARN of the CloudFront Function that rewrites eligible /app SPA navigations for the dev environment."
  value       = module.cloudfront.spa_rewrite_function_arn
}

output "cloudfront_spa_rewrite_function_name" {
  description = "Name of the CloudFront Function that rewrites eligible /app SPA navigations for the dev environment."
  value       = module.cloudfront.spa_rewrite_function_name
}

############################################
# API Gateway routed backend outputs
############################################

# These outputs expose the routed HTTP API for integration, deployment
# validation, and operational inspection.
output "api_gateway_api_id" {
  description = "ID of the routed HTTP API created for the dev environment."
  value       = module.api_gateway.api_id
}

output "api_gateway_api_arn" {
  description = "ARN of the routed HTTP API created for the dev environment."
  value       = module.api_gateway.api_arn
}

output "api_gateway_execution_arn" {
  description = "Execution ARN of the routed HTTP API created for the dev environment."
  value       = module.api_gateway.api_execution_arn
}

output "api_gateway_api_endpoint" {
  description = "Base invoke endpoint of the routed HTTP API created for the dev environment."
  value       = module.api_gateway.api_endpoint
}

output "api_gateway_stage_name" {
  description = "Stage name of the routed HTTP API created for the dev environment."
  value       = module.api_gateway.stage_name
}

output "api_gateway_stage_invoke_url" {
  description = "Stage-qualified invoke URL of the routed HTTP API created for the dev environment."
  value       = module.api_gateway.stage_invoke_url
}

output "api_gateway_jwt_authorizer_id" {
  description = "JWT authorizer ID of the routed HTTP API created for the dev environment."
  value       = module.api_gateway.jwt_authorizer_id
}

output "api_gateway_request_authorizer_ids" {
  description = "Map of logical Lambda request authorizer name to authorizer ID for the dev HTTP API."
  value       = module.api_gateway.request_authorizer_ids
}

output "api_gateway_route_ids" {
  description = "Map of logical route name to route ID for the dev HTTP API."
  value       = module.api_gateway.route_ids
}

output "api_gateway_route_keys" {
  description = "Map of logical route name to route key for the dev HTTP API."
  value       = module.api_gateway.route_keys
}

############################################
# CloudWatch observability outputs
############################################

# These outputs expose CloudWatch alarm and dashboard identities without
# coupling consumers to the observability module internals.
output "observability_alarm_names" {
  description = "Map of logical observability alarm key to CloudWatch alarm name for the dev environment."
  value       = module.observability.alarm_names
}

output "observability_alarm_arns" {
  description = "Map of logical observability alarm key to CloudWatch alarm ARN for the dev environment."
  value       = module.observability.alarm_arns
}

output "observability_dashboard_name" {
  description = "Name of the CloudWatch operational dashboard created for the dev environment."
  value       = module.observability.dashboard_name
}

output "observability_dashboard_arn" {
  description = "ARN of the CloudWatch operational dashboard created for the dev environment."
  value       = module.observability.dashboard_arn
}
