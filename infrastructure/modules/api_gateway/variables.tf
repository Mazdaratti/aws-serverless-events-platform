############################################
# Shared environment context
############################################

variable "name_prefix" {
  description = "Shared environment naming prefix used to derive API Gateway resource names."
  type        = string

  validation {
    condition     = trimspace(var.name_prefix) != ""
    error_message = "name_prefix must not be empty."
  }
}

variable "tags" {
  description = "Tags applied to API Gateway resources that support tagging."
  type        = map(string)
}

############################################
# HTTP API baseline inputs
############################################

variable "stage_name" {
  description = "Stage name for the HTTP API used by this environment slice."
  type        = string

  validation {
    condition     = trimspace(var.stage_name) != ""
    error_message = "stage_name must not be empty."
  }
}

variable "jwt_issuer" {
  description = "JWT issuer URL used by the HTTP API JWT authorizer."
  type        = string

  validation {
    condition     = trimspace(var.jwt_issuer) != ""
    error_message = "jwt_issuer must not be empty."
  }
}

variable "jwt_audience" {
  description = "JWT audience values accepted by the HTTP API JWT authorizer."
  type        = list(string)

  validation {
    condition = length(var.jwt_audience) > 0 && alltrue([
      for audience in var.jwt_audience :
      trimspace(audience) != ""
    ])
    error_message = "jwt_audience must contain at least one non-empty value."
  }
}

variable "request_authorizers" {
  description = <<-EOT
    Optional HTTP API Lambda request authorizers keyed by logical authorizer name.

    This supports mixed-mode routed behavior that cannot be expressed with the
    built-in JWT authorizer alone.
  EOT

  type = map(object({
    authorizer_uri                    = string
    lambda_function_name              = string
    identity_sources                  = optional(list(string))
    authorizer_credentials_arn        = optional(string)
    name                              = optional(string)
    authorizer_payload_format_version = optional(string, "2.0")
    enable_simple_responses           = optional(bool, true)
    authorizer_result_ttl_in_seconds  = optional(number, 0)
  }))

  default = {}

  validation {
    condition = alltrue([
      for authorizer in values(var.request_authorizers) :
      trimspace(authorizer.authorizer_uri) != ""
    ])
    error_message = "Each request authorizer authorizer_uri must be a non-empty string."
  }

  validation {
    condition = alltrue([
      for authorizer in values(var.request_authorizers) :
      trimspace(authorizer.lambda_function_name) != ""
    ])
    error_message = "Each request authorizer lambda_function_name must be a non-empty string."
  }

  validation {
    condition = alltrue([
      for authorizer in values(var.request_authorizers) :
      try(authorizer.identity_sources == null, true) || (
        length(authorizer.identity_sources) > 0 && alltrue([
          for identity_source in authorizer.identity_sources :
          trimspace(identity_source) != ""
        ])
      )
    ])
    error_message = "Each request authorizer identity_sources value must be omitted or contain at least one non-empty identity source."
  }

  validation {
    condition = alltrue([
      for authorizer in values(var.request_authorizers) :
      authorizer.authorizer_payload_format_version == "2.0"
    ])
    error_message = "Each request authorizer must use payload format version \"2.0\"."
  }

  validation {
    condition = alltrue([
      for authorizer in values(var.request_authorizers) :
      authorizer.authorizer_result_ttl_in_seconds >= 0
    ])
    error_message = "Each request authorizer authorizer_result_ttl_in_seconds must be zero or greater."
  }

  validation {
    condition = alltrue([
      for authorizer in values(var.request_authorizers) :
      try(authorizer.identity_sources != null, false) || authorizer.authorizer_result_ttl_in_seconds == 0
    ])
    error_message = "Each request authorizer without identity_sources must set authorizer_result_ttl_in_seconds to 0."
  }
}

############################################
# Route wiring inputs
############################################

variable "routes" {
  description = <<-EOT
    Map of HTTP API routes keyed by logical route name.

    This first module version stays intentionally small:
    - route_key defines the HTTP API route such as "POST /events"
    - lambda_invoke_arn defines the Lambda integration target
    - lambda_function_name defines the Lambda permission target
    - authorization_type supports public, JWT, and Lambda-authorized routes
    - authorizer_key is used only for CUSTOM routes to select one logical
      request authorizer from var.request_authorizers
  EOT

  type = map(object({
    route_key            = string
    lambda_invoke_arn    = string
    lambda_function_name = string
    authorization_type   = string
    authorizer_key       = optional(string)
  }))

  validation {
    condition = alltrue([
      for route in values(var.routes) :
      contains(["JWT", "NONE", "CUSTOM"], route.authorization_type)
    ])
    error_message = "Each route.authorization_type must be one of \"JWT\", \"NONE\", or \"CUSTOM\"."
  }

  validation {
    condition = alltrue([
      for route in values(var.routes) :
      route.authorization_type != "CUSTOM" || try(trimspace(route.authorizer_key) != "", false)
    ])
    error_message = "Each CUSTOM route must provide a non-empty authorizer_key."
  }

  validation {
    condition = alltrue([
      for route in values(var.routes) :
      route.authorization_type != "CUSTOM" || contains(keys(var.request_authorizers), route.authorizer_key)
    ])
    error_message = "Each CUSTOM route authorizer_key must match a key in var.request_authorizers."
  }

  validation {
    condition = alltrue([
      for route in values(var.routes) :
      route.authorization_type == "CUSTOM" || try(route.authorizer_key == null, true)
    ])
    error_message = "authorizer_key may only be set for CUSTOM routes."
  }
}
