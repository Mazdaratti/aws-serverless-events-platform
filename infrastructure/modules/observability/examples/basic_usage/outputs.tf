############################################
# CloudWatch alarm outputs
############################################

output "alarm_names" {
  description = "Map of logical alarm key to CloudWatch alarm name created by the example."
  value       = module.observability.alarm_names
}

output "alarm_arns" {
  description = "Map of logical alarm key to CloudWatch alarm ARN created by the example."
  value       = module.observability.alarm_arns
}

############################################
# CloudWatch dashboard outputs
############################################

output "dashboard_name" {
  description = "Name of the CloudWatch dashboard created by the example."
  value       = module.observability.dashboard_name
}

output "dashboard_arn" {
  description = "ARN of the CloudWatch dashboard created by the example."
  value       = module.observability.dashboard_arn
}
