############################################
# Shared module inputs
############################################

variable "name_prefix" {
  description = "Shared environment naming prefix used to derive the Terraform state bucket name when state_bucket_name is not set."
  type        = string

  validation {
    condition     = length(trimspace(var.name_prefix)) > 0
    error_message = "name_prefix must not be empty."
  }

  validation {
    condition     = length(var.name_prefix) <= 45
    error_message = "name_prefix must be 45 characters or fewer so the default Terraform state bucket name stays within the S3 63-character limit."
  }
}

variable "tags" {
  description = "Baseline tags passed from the environment root and extended with resource-specific Name tags inside the module."
  type        = map(string)

  validation {
    condition     = length(var.tags) > 0
    error_message = "tags must contain at least the baseline environment tags."
  }
}

############################################
# Terraform state bucket configuration
############################################

variable "state_bucket_name" {
  description = "Optional explicit globally unique S3 bucket name for Terraform state. When null, the module derives a name from name_prefix and a random suffix."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition = (
      var.state_bucket_name == null ||
      (
        length(trimspace(var.state_bucket_name)) >= 3 &&
        length(trimspace(var.state_bucket_name)) <= 63 &&
        var.state_bucket_name == trimspace(var.state_bucket_name) &&
        can(regex("^[a-z0-9][a-z0-9.-]*[a-z0-9]$", var.state_bucket_name)) &&
        !can(regex("\\.\\.", var.state_bucket_name)) &&
        !can(regex("^\\d+\\.\\d+\\.\\d+\\.\\d+$", var.state_bucket_name)) &&
        !can(regex("^xn--", var.state_bucket_name)) &&
        !can(regex("^sthree-", var.state_bucket_name)) &&
        !can(regex("^amzn-s3-demo-", var.state_bucket_name)) &&
        !can(regex("-s3alias$", var.state_bucket_name)) &&
        !can(regex("--ol-s3$", var.state_bucket_name)) &&
        !can(regex("\\.mrap$", var.state_bucket_name)) &&
        !can(regex("--x-s3$", var.state_bucket_name)) &&
        !can(regex("--table-s3$", var.state_bucket_name))
      )
    )
    error_message = "state_bucket_name must be null or a valid S3 general purpose bucket name: 3-63 characters, lowercase letters, numbers, periods, and hyphens; starting and ending with a letter or number; not IP-address formatted; and not using reserved S3 prefixes or suffixes."
  }
}
