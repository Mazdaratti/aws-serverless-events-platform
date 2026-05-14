############################################
# SES sender identity outputs
############################################

output "sender_email" {
  description = "SES sender email identity configured by the example."
  value       = module.ses.sender_email
}

output "sender_identity_arn" {
  description = "ARN of the SES sender email identity configured by the example."
  value       = module.ses.sender_identity_arn
}

############################################
# SES template outputs
############################################

output "template_names" {
  description = "Map of participant notification type to SES template name."
  value       = module.ses.template_names
}

output "template_arns" {
  description = "Map of participant notification type to SES template ARN."
  value       = module.ses.template_arns
}
