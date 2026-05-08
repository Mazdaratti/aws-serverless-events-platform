############################################
# SNS topic outputs
############################################

output "topic_name" {
  description = "Name of the SNS topic."
  value       = aws_sns_topic.this.name
}

output "topic_arn" {
  description = "ARN of the SNS topic."
  value       = aws_sns_topic.this.arn
}

output "topic_id" {
  description = "ID of the SNS topic."
  value       = aws_sns_topic.this.id
}

############################################
# Email subscription outputs
############################################

output "email_subscription_arns" {
  description = "Map of email endpoint to SNS email subscription ARN."
  value = {
    for email, subscription in aws_sns_topic_subscription.email :
    email => subscription.arn
  }
}
