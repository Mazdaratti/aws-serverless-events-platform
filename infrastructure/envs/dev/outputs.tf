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
