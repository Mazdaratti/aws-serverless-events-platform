############################################
# HTTP API baseline
############################################

resource "aws_apigatewayv2_api" "this" {
  name          = "${var.name_prefix}-http-api"
  protocol_type = "HTTP"

  # HTTP API CORS is optional in this module.
  #
  # When cors_configuration is null, API Gateway leaves CORS behavior
  # untouched. When it is set, API Gateway will manage browser preflight
  # responses and attach the configured CORS headers for this API.
  dynamic "cors_configuration" {
    for_each = var.cors_configuration == null ? [] : [var.cors_configuration]

    content {
      allow_origins     = cors_configuration.value.allow_origins
      allow_methods     = try(cors_configuration.value.allow_methods, null)
      allow_headers     = try(cors_configuration.value.allow_headers, null)
      expose_headers    = try(cors_configuration.value.expose_headers, null)
      allow_credentials = try(cors_configuration.value.allow_credentials, null)
      max_age           = try(cors_configuration.value.max_age, null)
    }
  }

  tags = var.tags
}

resource "aws_apigatewayv2_stage" "this" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = var.stage_name
  auto_deploy = true

  # Keep the stage-level contract strict in one place instead of trying to
  # express cross-variable relationships inside variable validation blocks.
  #
  # Access logging is optional, but when enabled the caller must provide both
  # a destination ARN and a non-empty log format. When disabled, both values
  # must stay null so the module input stays predictable and reviewable.
  lifecycle {
    precondition {
      condition = (
        var.access_log_enabled ?
        (
          trimspace(coalesce(var.access_log_destination_arn, "")) != "" &&
          trimspace(coalesce(var.access_log_format, "")) != ""
        ) :
        (
          var.access_log_destination_arn == null &&
          var.access_log_format == null
        )
      )
      error_message = "When access_log_enabled is true, access_log_destination_arn and access_log_format must both be non-empty. When access_log_enabled is false, both values must be null."
    }
  }

  # Stage access logging belongs to API Gateway itself, not to the Lambda
  # module. The caller owns the CloudWatch Logs log group and passes its ARN
  # into this module when logging is enabled.
  dynamic "access_log_settings" {
    for_each = var.access_log_enabled ? [1] : []

    content {
      destination_arn = var.access_log_destination_arn
      format          = var.access_log_format
    }
  }

  # Default stage throttling creates one baseline protection level for the
  # whole HTTP API. Individual routes can still override these defaults later
  # through route_settings when a smaller write-heavy surface needs tighter
  # limits than the rest of the API.
  dynamic "default_route_settings" {
    for_each = var.default_throttling_burst_limit == null ? [] : [1]

    content {
      throttling_burst_limit = var.default_throttling_burst_limit
      throttling_rate_limit  = var.default_throttling_rate_limit
    }
  }

  # Route settings stay intentionally narrow in this PR. The module currently
  # uses them only for per-route throttling overrides, which lets callers
  # tighten selected write paths without widening the module surface to other
  # API Gateway route-setting concerns.
  dynamic "route_settings" {
    for_each = local.route_settings

    content {
      route_key              = route_settings.key
      throttling_burst_limit = route_settings.value.throttling_burst_limit
      throttling_rate_limit  = route_settings.value.throttling_rate_limit
    }
  }

  tags = var.tags
}

############################################
# Built-in JWT authorizer
############################################

resource "aws_apigatewayv2_authorizer" "jwt" {
  api_id           = aws_apigatewayv2_api.this.id
  name             = "${var.name_prefix}-jwt-authorizer"
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]

  jwt_configuration {
    issuer   = var.jwt_issuer
    audience = var.jwt_audience
  }
}

############################################
# Lambda request authorizers
############################################

resource "aws_apigatewayv2_authorizer" "request" {
  for_each = var.request_authorizers

  api_id           = aws_apigatewayv2_api.this.id
  name             = coalesce(try(each.value.name, null), "${var.name_prefix}-${each.key}")
  authorizer_type  = "REQUEST"
  authorizer_uri   = each.value.authorizer_uri
  identity_sources = try(each.value.identity_sources, null)

  authorizer_credentials_arn        = try(each.value.authorizer_credentials_arn, null)
  authorizer_payload_format_version = each.value.authorizer_payload_format_version
  authorizer_result_ttl_in_seconds  = each.value.authorizer_result_ttl_in_seconds
  enable_simple_responses           = each.value.enable_simple_responses
}

############################################
# Route integrations
############################################

resource "aws_apigatewayv2_integration" "route" {
  for_each = local.route_integrations

  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  integration_uri        = each.value.lambda_invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "route" {
  for_each = local.route_integrations

  api_id    = aws_apigatewayv2_api.this.id
  route_key = each.value.route_key
  target    = "integrations/${aws_apigatewayv2_integration.route[each.key].id}"

  authorization_type = each.value.authorization_type
  authorizer_id = (
    each.value.authorization_type == "JWT" ? aws_apigatewayv2_authorizer.jwt.id :
    each.value.authorization_type == "CUSTOM" ? aws_apigatewayv2_authorizer.request[each.value.authorizer_key].id :
    null
  )
}

############################################
# Lambda invoke permissions
############################################

resource "aws_lambda_permission" "authorizer_invoke" {
  for_each = var.request_authorizers

  statement_id  = "AllowExecutionFromApiGatewayAuthorizer-${replace(replace(each.key, "-", "_"), " ", "_")}"
  action        = "lambda:InvokeFunction"
  function_name = each.value.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/authorizers/${aws_apigatewayv2_authorizer.request[each.key].id}"
}

resource "aws_lambda_permission" "api_gateway_invoke" {
  for_each = local.route_integrations

  statement_id  = "AllowExecutionFromApiGateway-${replace(replace(each.key, "-", "_"), " ", "_")}"
  action        = "lambda:InvokeFunction"
  function_name = each.value.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/*/${each.value.method}${each.value.path}"
}
