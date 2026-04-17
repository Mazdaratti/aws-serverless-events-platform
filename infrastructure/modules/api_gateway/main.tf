############################################
# HTTP API baseline
############################################

resource "aws_apigatewayv2_api" "this" {
  name          = "${var.name_prefix}-http-api"
  protocol_type = "HTTP"

  tags = var.tags
}

resource "aws_apigatewayv2_stage" "this" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = var.stage_name
  auto_deploy = true

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
  enable_simple_responses           = each.value.enable_simple_responses
}

############################################
# Route integrations
############################################

resource "aws_apigatewayv2_integration" "route" {
  for_each = local.routes

  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  integration_uri        = each.value.lambda_invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "route" {
  for_each = local.routes

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
  for_each = local.routes

  statement_id  = "AllowExecutionFromApiGateway-${replace(replace(each.key, "-", "_"), " ", "_")}"
  action        = "lambda:InvokeFunction"
  function_name = each.value.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/*/${each.value.method}${each.value.path}"
}
