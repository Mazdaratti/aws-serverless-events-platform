# HTTP API Gateway Module

This module creates the HTTP API Gateway resources for the serverless
events platform.

It is intentionally platform-specific rather than a general abstraction over
every API Gateway feature. The module owns one HTTP API, its stage,
authorizers, Lambda proxy integrations, routes, and invoke permissions.

Each environment root supplies the concrete Lambda functions, route
definitions, identity values, log destination, and operational settings. The
platform-wide API and authorization contracts are documented in the
[architecture guide](../../../docs/architecture.md) and
[platform behavior contract](../../../docs/platform-behavior.md).

---

## What This Module Creates

This module creates:

- one HTTP API
- one stage
- one built-in JWT authorizer
- zero or more Lambda request authorizers
- one Lambda proxy integration per declared route
- one HTTP API route per declared route
- Lambda invoke permissions for:
  - routed integrations
  - Lambda request authorizers

It can also configure:

- optional HTTP API CORS
- optional stage access logging
- optional default stage throttling
- optional per-route throttling overrides

The caller controls the stage name, route definitions, authorization modes,
logging, throttling, and optional CORS configuration.

---

## Module Boundary

The module owns:

- HTTP API creation
- stage creation
- route-to-Lambda proxy integration wiring
- route-level authorization wiring
- stage-level access logging configuration
- stage and route throttling configuration
- optional API-level CORS

It does not own:

- Lambda functions, execution roles, or log groups
- Cognito User Pools or application clients
- caller-owned API Gateway access log groups
- CloudFront distributions or WAF resources
- custom domains or Route 53 records
- REST API resources
- application request validation or authorization behavior

Those responsibilities belong to callers and the modules that own the
corresponding resources.

---

## Supported Route Shape

Route keys in this module use the form:

- `METHOD /path`

The supported HTTP methods are intentionally narrow:

- `GET`
- `POST`
- `PATCH`
- `DELETE`
- `OPTIONS`

These methods cover the platform's read, create, partial-update, delete, and
browser preflight route shapes.

The module does not allow:

- `PUT`
- `HEAD`
- `ANY`

Supporting another method requires an explicit module-interface change.

---

## Supported Authorization Modes

This module supports three route authorization modes:

- `NONE`
- `JWT`
- `CUSTOM`

### Public routes

Routes with `authorization_type = "NONE"` are publicly callable.

### JWT-protected routes

Routes with `authorization_type = "JWT"` use the built-in HTTP API JWT
authorizer configured from the caller-supplied issuer and audience.

### Lambda request-authorized routes

Routes with `authorization_type = "CUSTOM"` use one declared Lambda request
authorizer from `var.request_authorizers`.

This supports request-specific authorization without hardcoding application
behavior into the module.

---

## Lambda Proxy Integration Model

This module uses HTTP API Lambda proxy integrations with payload format version
`2.0`.

That is intentional:

- callers receive the standard HTTP API proxy request and response shape
- JWT and Lambda authorizer context can flow through without custom mapping
- the integration layer remains small and predictable

The module does not implement mapping templates, transformation layers, or
REST-API-style resource trees.

---

## Stage Operations

This module can optionally configure several stage-level operational controls.

### Access logging

HTTP API stage access logging is optional.

When enabled, the module configures API Gateway stage access logging only. It
does not create the CloudWatch Logs log group. The caller must create that log
group and pass its ARN into the module.

That ownership split is intentional:

- API Gateway stage logging configuration belongs here
- CloudWatch Logs resource ownership stays with the caller
- Lambda log groups remain outside this module

### Default throttling

The module can apply one default throttling baseline to the whole HTTP API
stage through:

- `default_throttling_burst_limit`
- `default_throttling_rate_limit`

This gives callers one default protection level for the API stage.

### Per-route throttling overrides

The module can also apply per-route throttling overrides directly on selected
route keys.

This is useful when a smaller write-heavy or abuse-sensitive surface should be
throttled more tightly than the rest of the API.

---

## Optional CORS Support

HTTP API CORS support is optional and disabled by default.

When `cors_configuration` is `null`, the module leaves CORS behavior untouched.
When it is set, API Gateway manages browser preflight behavior and attaches the
configured CORS headers for the HTTP API.

The caller remains responsible for choosing origins, methods, headers, and
credential behavior appropriate to its delivery topology.

---

## Input Validation

This module intentionally validates its interface strictly so invalid route or
authorizer definitions fail early.

Examples of guarded behavior include:

- route keys must use the expected `METHOD /path` shape
- only the supported platform methods are accepted:
  - `GET`
  - `POST`
  - `PATCH`
  - `DELETE`
  - `OPTIONS`
- route authorization mode must be one of:
  - `NONE`
  - `JWT`
  - `CUSTOM`
- `CUSTOM` routes must reference a declared request authorizer
- non-`CUSTOM` routes must not set `authorizer_key`
- stage throttling values must be provided as a burst/rate pair
- per-route throttling overrides must also be provided as a burst/rate pair
- request authorizer payload format stays pinned to HTTP API payload version
  `2.0`

This keeps the module precise without baking application-specific route
behavior into its implementation.

---

## Outputs

The module exposes:

- API identifiers and invoke values
- stage name and stage invoke URL
- JWT authorizer ID
- Lambda request authorizer IDs
- route IDs and route keys

Callers can use these values for edge routing, validation, and operational
integration without depending on Terraform resource internals.

---

## Example

This module includes a runnable example:

- `examples/basic_usage`

The example shows how to:

- build the shared `name_prefix`
- define the baseline tag map
- create a caller-owned API Gateway access log group
- create two tiny Lambda functions for:
  - ordinary route integration
  - the optional Lambda request-authorizer path
- enable stage access logging
- enable default stage throttling
- add per-route throttling overrides
- enable optional CORS
- call the module with:
  - one public route
  - one JWT-protected route
  - one Lambda request-authorized route

The example intentionally does not create CloudFront, WAF, custom domains,
Route 53 records, or frontend hosting resources.

Applying the example creates real API Gateway, Lambda, IAM, and CloudWatch Logs
resources and should be reviewed before use in an AWS account.

---

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | ~> 1.14.0 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | ~> 6.37 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_aws"></a> [aws](#provider\_aws) | 6.41.0 |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [aws_apigatewayv2_api.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apigatewayv2_api) | resource |
| [aws_apigatewayv2_authorizer.jwt](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apigatewayv2_authorizer) | resource |
| [aws_apigatewayv2_authorizer.request](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apigatewayv2_authorizer) | resource |
| [aws_apigatewayv2_integration.route](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apigatewayv2_integration) | resource |
| [aws_apigatewayv2_route.route](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apigatewayv2_route) | resource |
| [aws_apigatewayv2_stage.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/apigatewayv2_stage) | resource |
| [aws_lambda_permission.api_gateway_invoke](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_permission) | resource |
| [aws_lambda_permission.authorizer_invoke](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lambda_permission) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_access_log_destination_arn"></a> [access\_log\_destination\_arn](#input\_access\_log\_destination\_arn) | Caller-supplied CloudWatch Logs destination ARN for stage access logs when access\_log\_enabled is true. | `string` | `null` | no |
| <a name="input_access_log_enabled"></a> [access\_log\_enabled](#input\_access\_log\_enabled) | Whether the HTTP API stage writes API Gateway access logs to CloudWatch Logs. | `bool` | `false` | no |
| <a name="input_access_log_format"></a> [access\_log\_format](#input\_access\_log\_format) | Access log format string used by the HTTP API stage when access\_log\_enabled is true. | `string` | `null` | no |
| <a name="input_cors_configuration"></a> [cors\_configuration](#input\_cors\_configuration) | Optional HTTP API CORS configuration.<br/><br/>Leave null to disable module-managed CORS entirely. | <pre>object({<br/>    allow_origins     = list(string)<br/>    allow_methods     = optional(list(string))<br/>    allow_headers     = optional(list(string))<br/>    expose_headers    = optional(list(string))<br/>    allow_credentials = optional(bool)<br/>    max_age           = optional(number)<br/>  })</pre> | `null` | no |
| <a name="input_default_throttling_burst_limit"></a> [default\_throttling\_burst\_limit](#input\_default\_throttling\_burst\_limit) | Default burst throttling limit applied at the HTTP API stage when stage throttling is enabled. | `number` | `null` | no |
| <a name="input_default_throttling_rate_limit"></a> [default\_throttling\_rate\_limit](#input\_default\_throttling\_rate\_limit) | Default steady-state throttling rate limit applied at the HTTP API stage when stage throttling is enabled. | `number` | `null` | no |
| <a name="input_jwt_audience"></a> [jwt\_audience](#input\_jwt\_audience) | JWT audience values accepted by the HTTP API JWT authorizer. | `list(string)` | n/a | yes |
| <a name="input_jwt_issuer"></a> [jwt\_issuer](#input\_jwt\_issuer) | JWT issuer URL used by the HTTP API JWT authorizer. | `string` | n/a | yes |
| <a name="input_name_prefix"></a> [name\_prefix](#input\_name\_prefix) | Shared environment naming prefix used to derive API Gateway resource names. | `string` | n/a | yes |
| <a name="input_request_authorizers"></a> [request\_authorizers](#input\_request\_authorizers) | Optional HTTP API Lambda request authorizers keyed by logical authorizer name.<br/><br/>This supports mixed-mode routed behavior that cannot be expressed with the<br/>built-in JWT authorizer alone. | <pre>map(object({<br/>    authorizer_uri                    = string<br/>    lambda_function_name              = string<br/>    identity_sources                  = optional(list(string))<br/>    authorizer_credentials_arn        = optional(string)<br/>    name                              = optional(string)<br/>    authorizer_payload_format_version = optional(string, "2.0")<br/>    enable_simple_responses           = bool<br/>    authorizer_result_ttl_in_seconds  = optional(number, 0)<br/>  }))</pre> | `{}` | no |
| <a name="input_routes"></a> [routes](#input\_routes) | Map of HTTP API routes keyed by logical route name.<br/><br/>Supported route behavior:<br/>- route\_key defines the HTTP API route such as "POST /events"<br/>- lambda\_invoke\_arn defines the Lambda integration target<br/>- lambda\_function\_name defines the Lambda permission target<br/>- authorization\_type supports public, JWT, and Lambda-authorized routes<br/>- authorizer\_key is used only for CUSTOM routes to select one logical<br/>  request authorizer from var.request\_authorizers<br/>- optional per-route throttling overrides can be supplied directly | <pre>map(object({<br/>    route_key              = string<br/>    lambda_invoke_arn      = string<br/>    lambda_function_name   = string<br/>    authorization_type     = string<br/>    authorizer_key         = optional(string)<br/>    throttling_burst_limit = optional(number)<br/>    throttling_rate_limit  = optional(number)<br/>  }))</pre> | n/a | yes |
| <a name="input_stage_name"></a> [stage\_name](#input\_stage\_name) | Stage name for the HTTP API used by this environment slice. | `string` | n/a | yes |
| <a name="input_tags"></a> [tags](#input\_tags) | Baseline tags passed from the environment root and extended with resource-specific tags inside the module. | `map(string)` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_api_arn"></a> [api\_arn](#output\_api\_arn) | ARN of the HTTP API created by the module. |
| <a name="output_api_endpoint"></a> [api\_endpoint](#output\_api\_endpoint) | Base invoke endpoint of the HTTP API created by the module. |
| <a name="output_api_execution_arn"></a> [api\_execution\_arn](#output\_api\_execution\_arn) | Execution ARN of the HTTP API created by the module. |
| <a name="output_api_id"></a> [api\_id](#output\_api\_id) | ID of the HTTP API created by the module. |
| <a name="output_jwt_authorizer_id"></a> [jwt\_authorizer\_id](#output\_jwt\_authorizer\_id) | ID of the JWT authorizer created by the module. |
| <a name="output_request_authorizer_ids"></a> [request\_authorizer\_ids](#output\_request\_authorizer\_ids) | Map of logical Lambda request authorizer name to HTTP API authorizer ID. |
| <a name="output_route_ids"></a> [route\_ids](#output\_route\_ids) | Map of logical route name to HTTP API route ID created by the module. |
| <a name="output_route_keys"></a> [route\_keys](#output\_route\_keys) | Map of logical route name to HTTP API route key created by the module. |
| <a name="output_stage_invoke_url"></a> [stage\_invoke\_url](#output\_stage\_invoke\_url) | Stage-qualified invoke URL for the HTTP API created by the module. |
| <a name="output_stage_name"></a> [stage\_name](#output\_stage\_name) | Stage name created by the module. |
<!-- END_TF_DOCS -->
