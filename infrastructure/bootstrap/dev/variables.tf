############################################
# Core bootstrap identity
############################################

variable "project_name" {
  description = "Project name used as the shared naming and tagging baseline for dev bootstrap resources."
  type        = string

  validation {
    condition     = length(trimspace(var.project_name)) > 0
    error_message = "project_name must not be empty."
  }
}

variable "environment" {
  description = "Environment name used for dev bootstrap resource naming and the generated backend configuration."
  type        = string
  default     = "dev"

  validation {
    condition = (
      var.environment == trimspace(var.environment) &&
      can(regex("^[a-z0-9]+(?:-[a-z0-9]+)*$", var.environment))
    )
    error_message = "environment must contain lowercase letters, numbers, and hyphens only, with no leading or trailing whitespace."
  }

  validation {
    condition     = length("${var.project_name}-${var.environment}") <= 45
    error_message = "project_name and environment together must produce a name_prefix of 45 characters or fewer so the default Terraform state bucket name stays within the S3 63-character limit."
  }
}

variable "aws_region" {
  description = "AWS region where dev bootstrap resources are created."
  type        = string
  default     = "eu-central-1"

  validation {
    condition     = length(trimspace(var.aws_region)) > 0
    error_message = "aws_region must not be empty."
  }
}

variable "additional_tags" {
  description = "Additional tags merged into the bootstrap provider default tags."
  type        = map(string)
  default     = {}
}

############################################
# Remote backend configuration
############################################

variable "state_bucket_name" {
  description = "Optional explicit globally unique S3 bucket name for dev Terraform state. When null, bootstrap derives a name from the environment prefix and a random suffix."
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

############################################
# GitHub OIDC configuration
############################################

variable "github_org" {
  description = "GitHub organization or user name that owns the repository allowed to assume the bootstrap-created OIDC role."
  type        = string

  validation {
    condition     = length(trimspace(var.github_org)) > 0
    error_message = "github_org must not be empty."
  }
}

variable "github_repo" {
  description = "GitHub repository name allowed to assume the bootstrap-created OIDC role."
  type        = string

  validation {
    condition     = length(trimspace(var.github_repo)) > 0
    error_message = "github_repo must not be empty."
  }
}

variable "github_branch" {
  description = "GitHub branch name allowed to assume the bootstrap-created OIDC role."
  type        = string
  default     = "main"

  validation {
    condition     = length(trimspace(var.github_branch)) > 0
    error_message = "github_branch must not be empty."
  }
}

variable "create_permissions_boundary" {
  description = "Whether to create and attach the repo-aligned permissions boundary to the GitHub Actions OIDC role."
  type        = bool
  default     = true
}
