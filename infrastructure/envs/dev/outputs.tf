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
