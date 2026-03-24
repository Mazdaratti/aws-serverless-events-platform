############################################
# Events table outputs
############################################

output "events_table_name" {
  description = "Name of the DynamoDB events table used to store canonical event records."
  value       = aws_dynamodb_table.events.name
}

output "events_table_arn" {
  description = "ARN of the DynamoDB events table used to store canonical event records."
  value       = aws_dynamodb_table.events.arn
}

############################################
# RSVP table outputs
############################################

output "rsvps_table_name" {
  description = "Name of the DynamoDB RSVP table used to store canonical RSVP membership records."
  value       = aws_dynamodb_table.rsvps.name
}

output "rsvps_table_arn" {
  description = "ARN of the DynamoDB RSVP table used to store canonical RSVP membership records."
  value       = aws_dynamodb_table.rsvps.arn
}
