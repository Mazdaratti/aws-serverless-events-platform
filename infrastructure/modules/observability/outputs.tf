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
