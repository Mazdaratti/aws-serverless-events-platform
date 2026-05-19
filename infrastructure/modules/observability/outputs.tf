############################################
# CloudWatch alarm outputs
############################################

output "alarm_names" {
  description = "Map of logical alarm key to CloudWatch alarm name."
  value = {
    for alarm_key, alarm in aws_cloudwatch_metric_alarm.metric :
    alarm_key => alarm.alarm_name
  }
}

output "alarm_arns" {
  description = "Map of logical alarm key to CloudWatch alarm ARN."
  value = {
    for alarm_key, alarm in aws_cloudwatch_metric_alarm.metric :
    alarm_key => alarm.arn
  }
}

############################################
# CloudWatch dashboard outputs
############################################

output "dashboard_name" {
  description = "Name of the CloudWatch dashboard created by the module, or null when dashboard creation is disabled."
  value       = var.dashboard_enabled ? aws_cloudwatch_dashboard.this[0].dashboard_name : null
}

output "dashboard_arn" {
  description = "ARN of the CloudWatch dashboard created by the module, or null when dashboard creation is disabled."
  value       = var.dashboard_enabled ? aws_cloudwatch_dashboard.this[0].dashboard_arn : null
}
