############################################
# Event bus outputs
############################################

output "event_bus_name" {
  description = "Name of the custom EventBridge event bus."
  value       = aws_cloudwatch_event_bus.this.name
}

output "event_bus_arn" {
  description = "ARN of the custom EventBridge event bus."
  value       = aws_cloudwatch_event_bus.this.arn
}

output "event_bus_id" {
  description = "ID of the custom EventBridge event bus."
  value       = aws_cloudwatch_event_bus.this.id
}

############################################
# Event rule outputs
############################################

output "rule_names" {
  description = "Map of logical rule key to EventBridge rule name."
  value = {
    for rule_key, rule in aws_cloudwatch_event_rule.this :
    rule_key => rule.name
  }
}

output "rule_arns" {
  description = "Map of logical rule key to EventBridge rule ARN."
  value = {
    for rule_key, rule in aws_cloudwatch_event_rule.this :
    rule_key => rule.arn
  }
}

############################################
# Event target outputs
############################################

output "target_ids" {
  description = "Map of logical target key in rule.target form to EventBridge target ID."
  value = {
    for target_key, target in aws_cloudwatch_event_target.this :
    target_key => target.target_id
  }
}

output "target_arns" {
  description = "Map of logical target key in rule.target form to target ARN."
  value = {
    for target_key, target in aws_cloudwatch_event_target.this :
    target_key => target.arn
  }
}
