############################################
# Example verification outputs
############################################

output "event_bus_name" {
  description = "Name of the custom EventBridge event bus created by the example."
  value       = module.eventbridge.event_bus_name
}

output "event_bus_arn" {
  description = "ARN of the custom EventBridge event bus created by the example."
  value       = module.eventbridge.event_bus_arn
}

output "event_bus_id" {
  description = "ID of the custom EventBridge event bus created by the example."
  value       = module.eventbridge.event_bus_id
}

output "rule_names" {
  description = "EventBridge rule names created by the example."
  value       = module.eventbridge.rule_names
}

output "rule_arns" {
  description = "EventBridge rule ARNs created by the example."
  value       = module.eventbridge.rule_arns
}

output "target_ids" {
  description = "EventBridge target IDs created by the example."
  value       = module.eventbridge.target_ids
}

output "target_arns" {
  description = "EventBridge target ARNs created by the example."
  value       = module.eventbridge.target_arns
}
