############################################
# Example verification outputs
############################################

output "function_names" {
  description = "Rendered Lambda function names created by the basic_usage example."
  value       = module.lambda.function_names
}

output "function_arns" {
  description = "Rendered Lambda function ARNs created by the basic_usage example."
  value       = module.lambda.function_arns
}

output "invoke_arns" {
  description = "Rendered Lambda invoke ARNs created by the basic_usage example."
  value       = module.lambda.invoke_arns
}

output "log_group_names" {
  description = "Rendered CloudWatch Logs log group names created by the basic_usage example."
  value       = module.lambda.log_group_names
}

output "log_group_arns" {
  description = "Rendered CloudWatch Logs log group ARNs created by the basic_usage example."
  value       = module.lambda.log_group_arns
}
