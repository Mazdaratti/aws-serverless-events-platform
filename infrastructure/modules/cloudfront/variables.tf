############################################
# Shared module inputs
############################################

variable "name_prefix" {
  description = "Shared environment naming prefix used to derive CloudFront distribution resource names."
  type        = string

  validation {
    condition     = length(trimspace(var.name_prefix)) > 0
    error_message = "name_prefix must not be empty."
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
# Distribution behavior
############################################

variable "enabled" {
  description = "Whether the CloudFront distribution is enabled."
  type        = bool
  default     = true
}

variable "price_class" {
  description = "CloudFront price class used to keep the first edge-delivery baseline cost-aware."
  type        = string
  default     = "PriceClass_100"

  validation {
    condition     = contains(["PriceClass_100", "PriceClass_200", "PriceClass_All"], var.price_class)
    error_message = "price_class must be one of PriceClass_100, PriceClass_200, or PriceClass_All."
  }
}

variable "default_root_object" {
  description = "Default object CloudFront returns for requests to the distribution root."
  type        = string
  default     = "index.html"

  validation {
    condition     = length(trimspace(var.default_root_object)) > 0
    error_message = "default_root_object must not be empty."
  }
}

variable "web_acl_arn" {
  description = "Optional AWS WAFv2 Web ACL ARN to associate with the CloudFront distribution."
  type        = string
  default     = null

  validation {
    condition = (
      var.web_acl_arn == null ||
      length(trimspace(var.web_acl_arn)) > 0
    )
    error_message = "web_acl_arn must be null or a non-empty string."
  }
}

############################################
# S3 frontend origin
############################################

variable "s3_origin_bucket_regional_domain_name" {
  description = "Regional domain name of the private S3 bucket used as the frontend asset origin."
  type        = string

  validation {
    condition     = length(trimspace(var.s3_origin_bucket_regional_domain_name)) > 0
    error_message = "s3_origin_bucket_regional_domain_name must not be empty."
  }
}

variable "s3_origin_id" {
  description = "Stable CloudFront origin ID used for the private S3 frontend origin."
  type        = string
  default     = "s3-frontend-origin"

  validation {
    condition     = length(trimspace(var.s3_origin_id)) > 0
    error_message = "s3_origin_id must not be empty."
  }
}

############################################
# API Gateway origin
############################################

variable "api_origin_domain_name" {
  description = "Domain name of the API Gateway origin, without protocol or stage path."
  type        = string

  validation {
    condition     = length(trimspace(var.api_origin_domain_name)) > 0
    error_message = "api_origin_domain_name must not be empty."
  }
}

variable "api_origin_id" {
  description = "Stable CloudFront origin ID used for the API Gateway backend origin."
  type        = string
  default     = "api-gateway-origin"

  validation {
    condition     = length(trimspace(var.api_origin_id)) > 0
    error_message = "api_origin_id must not be empty."
  }
}

variable "api_origin_path" {
  description = "Optional API Gateway stage path that CloudFront appends before forwarding requests to the API origin."
  type        = string
  default     = null

  validation {
    condition = (
      var.api_origin_path == null ||
      (
        startswith(var.api_origin_path, "/") &&
        !endswith(var.api_origin_path, "/") &&
        length(trimspace(var.api_origin_path)) > 1
      )
    )
    error_message = "api_origin_path must be null or start with '/' and must not end with '/'."
  }
}
