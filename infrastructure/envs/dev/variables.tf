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
