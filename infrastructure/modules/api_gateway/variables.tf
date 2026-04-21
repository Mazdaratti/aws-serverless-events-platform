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
  default     = {}
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

############################################
# Optional API-level CORS support
############################################

variable "cors_configuration" {
  description = <<-EOT
    Optional HTTP API CORS configuration.

    Leave null to disable module-managed CORS entirely.
  EOT

  type = object({
    allow_origins     = list(string)
    allow_methods     = optional(list(string))
    allow_headers     = optional(list(string))
    expose_headers    = optional(list(string))
    allow_credentials = optional(bool)
    max_age           = optional(number)
  })

  default = null

  validation {
    condition = (
      var.cors_configuration == null ||
      length(var.cors_configuration.allow_origins) > 0
    )
    error_message = "cors_configuration.allow_origins must contain at least one value when cors_configuration is set."
  }

  validation {
    condition = (
      var.cors_configuration == null ||
      alltrue([
        for origin in var.cors_configuration.allow_origins :
        trimspace(origin) != ""
      ])
    )
    error_message = "cors_configuration.allow_origins must contain only non-empty values."
  }

  validation {
    condition = (
      var.cors_configuration == null ||
      try(var.cors_configuration.allow_methods == null, true) ||
      (
        length(var.cors_configuration.allow_methods) > 0 &&
        alltrue([
          for method in var.cors_configuration.allow_methods :
          contains(["GET", "POST", "PATCH", "DELETE", "OPTIONS"], upper(trimspace(method)))
        ])
      )
    )
    error_message = "cors_configuration.allow_methods must be omitted or contain only GET, POST, PATCH, DELETE, or OPTIONS."
  }

  validation {
    condition = (
      var.cors_configuration == null ||
      try(var.cors_configuration.allow_headers == null, true) ||
      alltrue([
        for header in var.cors_configuration.allow_headers :
        trimspace(header) != ""
      ])
    )
    error_message = "cors_configuration.allow_headers must be omitted or contain only non-empty values."
  }

  validation {
    condition = (
      var.cors_configuration == null ||
      try(var.cors_configuration.expose_headers == null, true) ||
      alltrue([
        for header in var.cors_configuration.expose_headers :
        trimspace(header) != ""
      ])
    )
    error_message = "cors_configuration.expose_headers must be omitted or contain only non-empty values."
  }

  validation {
    condition = (
      var.cors_configuration == null ||
      try(var.cors_configuration.max_age == null, true) ||
      (
        var.cors_configuration.max_age >= 0 &&
        floor(var.cors_configuration.max_age) == var.cors_configuration.max_age
      )
    )
    error_message = "cors_configuration.max_age must be omitted or set to an integer value greater than or equal to 0."
  }
}

############################################
# Optional stage access logging
############################################

variable "access_log_enabled" {
  description = "Whether the HTTP API stage writes API Gateway access logs to CloudWatch Logs."
  type        = bool
  default     = false
}

variable "access_log_destination_arn" {
  description = "Caller-supplied CloudWatch Logs destination ARN for stage access logs when access_log_enabled is true."
  type        = string
  default     = null

  validation {
    condition = (
      var.access_log_destination_arn == null ||
      trimspace(var.access_log_destination_arn) != ""
    )
    error_message = "access_log_destination_arn must be null or a non-empty string."
  }
}

variable "access_log_format" {
  description = "Access log format string used by the HTTP API stage when access_log_enabled is true."
  type        = string
  default     = null

  validation {
    condition = (
      var.access_log_format == null ||
      trimspace(var.access_log_format) != ""
    )
    error_message = "access_log_format must be null or a non-empty string."
  }
}

############################################
# Optional stage default throttling
############################################

variable "default_throttling_burst_limit" {
  description = "Default burst throttling limit applied at the HTTP API stage when stage throttling is enabled."
  type        = number
  default     = null

  validation {
    condition = (
      var.default_throttling_burst_limit == null ||
      (
        var.default_throttling_burst_limit > 0 &&
        floor(var.default_throttling_burst_limit) == var.default_throttling_burst_limit
      )
    )
    error_message = "default_throttling_burst_limit must be null or a positive integer."
  }
}

variable "default_throttling_rate_limit" {
  description = "Default steady-state throttling rate limit applied at the HTTP API stage when stage throttling is enabled."
  type        = number
  default     = null

  validation {
    condition = (
      var.default_throttling_rate_limit == null ||
      var.default_throttling_rate_limit > 0
    )
    error_message = "default_throttling_rate_limit must be null or a positive number."
  }

  validation {
    condition = (
      (var.default_throttling_burst_limit == null && var.default_throttling_rate_limit == null) ||
      (var.default_throttling_burst_limit != null && var.default_throttling_rate_limit != null)
    )
    error_message = "default_throttling_burst_limit and default_throttling_rate_limit must either both be set or both be null."
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
    enable_simple_responses           = bool
    authorizer_result_ttl_in_seconds  = optional(number, 0)
  }))

  default = {}

  validation {
    condition = alltrue([
      for authorizer_key, authorizer in var.request_authorizers :
      trimspace(authorizer_key) != ""
    ])
    error_message = "request_authorizers keys must be non-empty strings."
  }

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
      try(authorizer.name == null, true) || trimspace(authorizer.name) != ""
    ])
    error_message = "Each request authorizer name must be omitted or set to a non-empty string."
  }

  validation {
    condition = alltrue([
      for authorizer in values(var.request_authorizers) :
      try(authorizer.authorizer_credentials_arn == null, true) || trimspace(authorizer.authorizer_credentials_arn) != ""
    ])
    error_message = "Each request authorizer authorizer_credentials_arn must be omitted or set to a non-empty string."
  }

  validation {
    condition = alltrue([
      for authorizer in values(var.request_authorizers) :
      try(authorizer.identity_sources == null, true) || (
        length(authorizer.identity_sources) > 0 && alltrue([
          for identity_source in authorizer.identity_sources :
          trimspace(identity_source) != "" &&
          length(regexall("^\\$request\\..+", trimspace(identity_source))) > 0
        ])
      )
    ])
    error_message = "Each request authorizer identity_sources value must be omitted or contain one or more non-empty values starting with \"$request.\"."
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
      floor(authorizer.authorizer_result_ttl_in_seconds) == authorizer.authorizer_result_ttl_in_seconds
    ])
    error_message = "Each request authorizer authorizer_result_ttl_in_seconds must be an integer."
  }

  validation {
    condition = alltrue([
      for authorizer in values(var.request_authorizers) :
      authorizer.authorizer_result_ttl_in_seconds >= 0 &&
      authorizer.authorizer_result_ttl_in_seconds <= 3600
    ])
    error_message = "Each request authorizer authorizer_result_ttl_in_seconds must be between 0 and 3600."
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

    Supported route behavior:
    - route_key defines the HTTP API route such as "POST /events"
    - lambda_invoke_arn defines the Lambda integration target
    - lambda_function_name defines the Lambda permission target
    - authorization_type supports public, JWT, and Lambda-authorized routes
    - authorizer_key is used only for CUSTOM routes to select one logical
      request authorizer from var.request_authorizers
    - optional per-route throttling overrides can be supplied directly
  EOT

  type = map(object({
    route_key              = string
    lambda_invoke_arn      = string
    lambda_function_name   = string
    authorization_type     = string
    authorizer_key         = optional(string)
    throttling_burst_limit = optional(number)
    throttling_rate_limit  = optional(number)
  }))

  validation {
    condition = length(distinct([
      for route in values(var.routes) :
      trimspace(route.route_key)
    ])) == length(values(var.routes))
    error_message = "Each route.route_key must be unique across var.routes."
  }

  validation {
    condition = alltrue([
      for route in values(var.routes) :
      trimspace(route.route_key) != "" &&
      trimspace(route.route_key) == route.route_key
    ])
    error_message = "Each route.route_key must be a non-empty string with no leading or trailing whitespace."
  }

  validation {
    condition = alltrue([
      for route in values(var.routes) :
      length(regexall("^(GET|POST|PATCH|DELETE|OPTIONS) /\\S*$", route.route_key)) > 0
    ])
    error_message = "Each route.route_key must match \"<METHOD> <PATH>\", where METHOD is one of GET, POST, PATCH, DELETE, or OPTIONS and PATH starts with '/'."
  }

  validation {
    condition = alltrue([
      for route in values(var.routes) :
      trimspace(route.lambda_invoke_arn) != ""
    ])
    error_message = "Each route.lambda_invoke_arn must be a non-empty string."
  }

  validation {
    condition = alltrue([
      for route in values(var.routes) :
      trimspace(route.lambda_function_name) != ""
    ])
    error_message = "Each route.lambda_function_name must be a non-empty string."
  }

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

  validation {
    condition = alltrue([
      for route in values(var.routes) :
      (
        try(route.throttling_burst_limit, null) == null &&
        try(route.throttling_rate_limit, null) == null
      ) ||
      (
        try(route.throttling_burst_limit, null) != null &&
        try(route.throttling_rate_limit, null) != null
      )
    ])
    error_message = "Each route must either set both throttling_burst_limit and throttling_rate_limit or leave both unset."
  }

  validation {
    condition = alltrue([
      for route in values(var.routes) :
      try(route.throttling_burst_limit, null) == null || (
        route.throttling_burst_limit > 0 &&
        floor(route.throttling_burst_limit) == route.throttling_burst_limit
      )
    ])
    error_message = "Each route.throttling_burst_limit must be omitted or set to a positive integer."
  }

  validation {
    condition = alltrue([
      for route in values(var.routes) :
      try(route.throttling_rate_limit, null) == null || route.throttling_rate_limit > 0
    ])
    error_message = "Each route.throttling_rate_limit must be omitted or set to a positive number."
  }
}
