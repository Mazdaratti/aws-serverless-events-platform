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
    - authorization_type keeps the route contract close to the future API
      shape while this first slice still uses only JWT-protected routes
  EOT

  type = map(object({
    route_key            = string
    lambda_invoke_arn    = string
    lambda_function_name = string
    authorization_type   = string
  }))

  validation {
    condition = alltrue([
      for route in values(var.routes) :
      contains(["JWT", "NONE"], route.authorization_type)
    ])
    error_message = "Each route.authorization_type must be either \"JWT\" or \"NONE\" in this module version."
  }
}
