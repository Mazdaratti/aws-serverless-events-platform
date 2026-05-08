############################################
# Example verification outputs
############################################

output "topic_name" {
  description = "Name of the SNS topic created by the example."
  value       = module.sns.topic_name
}

output "topic_arn" {
  description = "ARN of the SNS topic created by the example."
  value       = module.sns.topic_arn
}

output "topic_id" {
  description = "ID of the SNS topic created by the example."
  value       = module.sns.topic_id
}

output "email_subscription_arns" {
  description = "Email subscription ARNs created by the example."
  value       = module.sns.email_subscription_arns
}
