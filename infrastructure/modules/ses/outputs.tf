############################################
# SES sender identity outputs
############################################

output "sender_email" {
  description = "SES sender email identity configured for participant notifications."
  value       = aws_ses_email_identity.sender.email
}

output "sender_identity_arn" {
  description = "ARN of the SES sender email identity."
  value       = aws_ses_email_identity.sender.arn
}

############################################
# SES template outputs
############################################

output "template_names" {
  description = "Map of participant notification type to SES template name."
  value = {
    event_updated   = aws_ses_template.event_updated.name
    event_cancelled = aws_ses_template.event_cancelled.name
  }
}

output "template_arns" {
  description = "Map of participant notification type to SES template ARN."
  value = {
    event_updated   = aws_ses_template.event_updated.arn
    event_cancelled = aws_ses_template.event_cancelled.arn
  }
}
