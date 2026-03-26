############################################
# Example verification outputs
############################################

output "queue_names" {
  description = "Rendered primary queue names created by the basic_usage example."
  value       = module.sqs.queue_names
}

output "queue_arns" {
  description = "Rendered primary queue ARNs created by the basic_usage example."
  value       = module.sqs.queue_arns
}

output "queue_urls" {
  description = "Rendered primary queue URLs created by the basic_usage example."
  value       = module.sqs.queue_urls
}

output "dlq_names" {
  description = "Rendered DLQ names created by the basic_usage example."
  value       = module.sqs.dlq_names
}

output "dlq_arns" {
  description = "Rendered DLQ ARNs created by the basic_usage example."
  value       = module.sqs.dlq_arns
}

output "dlq_urls" {
  description = "Rendered DLQ URLs created by the basic_usage example."
  value       = module.sqs.dlq_urls
}
