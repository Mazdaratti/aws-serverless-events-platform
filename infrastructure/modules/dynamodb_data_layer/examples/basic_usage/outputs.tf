############################################
# Example verification outputs
############################################

output "events_table_name" {
  description = "Name of the events table created by the basic_usage example."
  value       = module.dynamodb_data_layer.events_table_name
}

output "events_table_arn" {
  description = "ARN of the events table created by the basic_usage example."
  value       = module.dynamodb_data_layer.events_table_arn
}

output "rsvps_table_name" {
  description = "Name of the RSVP table created by the basic_usage example."
  value       = module.dynamodb_data_layer.rsvps_table_name
}

output "rsvps_table_arn" {
  description = "ARN of the RSVP table created by the basic_usage example."
  value       = module.dynamodb_data_layer.rsvps_table_arn
}
