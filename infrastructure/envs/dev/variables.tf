############################################
# Core environment identity
############################################

variable "project_name" {
  description = "Project name used for naming and tagging resources."
  type        = string

  validation {
    condition     = length(trimspace(var.project_name)) > 0
    error_message = "project_name must not be empty."
  }
}

variable "environment" {
  description = "Deployment environment name."
  type        = string

  validation {
    condition     = length(trimspace(var.environment)) > 0
    error_message = "environment must not be empty."
  }
}

############################################
# AWS configuration
############################################

variable "aws_region" {
  description = "AWS region where resources will be deployed."
  type        = string

  validation {
    condition     = length(trimspace(var.aws_region)) > 0
    error_message = "aws_region must not be empty."
  }
}

############################################
# Environment behavior overrides
############################################

variable "dynamodb_point_in_time_recovery_enabled" {
  description = "Enable point-in-time recovery for DynamoDB tables in this environment."
  type        = bool
  default     = false
}

variable "enable_waf" {
  description = "Whether to create and attach the CloudFront-scoped WAF Web ACL in this dev environment."
  type        = bool
  default     = false
}

############################################
# Admin notification subscriptions
############################################

variable "sns_admin_email_subscriptions" {
  description = "Admin or developer email endpoints to subscribe to the SNS admin notification topic in dev. Email subscriptions require confirmation before receiving messages."
  type        = set(string)
  default     = []

  validation {
    condition = alltrue([
      for email in var.sns_admin_email_subscriptions :
      length(trimspace(email)) > 0
    ])
    error_message = "sns_admin_email_subscriptions must contain only non-empty strings."
  }

  validation {
    condition = alltrue([
      for email in var.sns_admin_email_subscriptions :
      trimspace(email) == email
    ])
    error_message = "sns_admin_email_subscriptions values must not contain leading or trailing whitespace."
  }
}

############################################
# Participant email sender identity
############################################

variable "ses_sender_email" {
  description = "Dedicated project inbox email address to verify as the SES sender identity for participant notifications in dev."
  type        = string

  validation {
    condition     = can(regex("^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$", var.ses_sender_email))
    error_message = "ses_sender_email must be a valid email-like address."
  }

  validation {
    condition     = trimspace(var.ses_sender_email) == var.ses_sender_email
    error_message = "ses_sender_email must not contain leading or trailing whitespace."
  }
}
