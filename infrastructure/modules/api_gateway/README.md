# HTTP API Backend Baseline

This module creates the reusable HTTP API backend baseline for the serverless
events platform.

It is intentionally platform-specific. The goal is not to provide a generic API
Gateway framework or a broad abstraction over every API Gateway feature.
Instead, this module defines the concrete HTTP API delivery layer that the
current Lambda workloads, Cognito identity baseline, and later environment
composition depend on.

This module is HTTP-API-backend-only in v1.

---

## What This Module Creates

This module currently creates:

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

This keeps the routed API baseline small, reviewable, and aligned with the
current platform rollout.

---

## Why This Module Stays HTTP API-Focused

This step is focused on the reusable API Gateway backend layer the platform
clearly needs next:

- HTTP API creation
- stage creation
- route-to-Lambda proxy integration wiring
- route-level authorization wiring
- stage-level access logging configuration
- stage and route throttling configuration
- optional API-level CORS

The module does not create CloudFront distributions, WAF resources, custom
domains, Route 53 records, API Gateway REST API resources, API Gateway X-Ray
tracing, or Lambda log groups. Those concerns may become relevant later, but
they are intentionally outside the scope of this module baseline.

Keeping the module limited to HTTP API backend delivery makes the design easier
to understand and preserves the current ownership boundaries:

- Cognito identity stays in `modules/cognito`
- Lambda deployment and Lambda log groups stay in `modules/lambda`
- edge delivery concerns stay outside this module
- `envs/dev` stays thin and composition-focused

---

## Supported Route Shape

Route keys in this module use the form:

- `METHOD /path`

The currently allowed HTTP methods are intentionally narrow:

- `GET`
- `POST`
- `PATCH`
- `DELETE`
- `OPTIONS`

That is deliberate.

- `GET`, `POST`, and `PATCH` match the platform's current routed API shape.
- `DELETE` is allowed now because hard-delete or cleanup-style admin endpoints
  are a plausible future extension for this platform, even though they are not
  part of the current routed baseline yet.
- `OPTIONS` is allowed now because browser-based frontend traffic will later
  need CORS preflight support when the frontend delivery layer is introduced.

The module does not currently allow broader HTTP API method values such as:

- `PUT`
- `HEAD`
- `ANY`

This keeps the reusable module aligned with the platform's current routed API
shape and avoids widening the public module surface before those methods are
actually needed.

---

## Supported Authorization Modes

This module currently supports three practical route authorization modes:

- `NONE`
- `JWT`
- `CUSTOM`

### Public routes

Routes with `authorization_type = "NONE"` stay publicly callable.

This is the current fit for routes such as:

- broad public event listing
- public single-event reads

### JWT-protected routes

Routes with `authorization_type = "JWT"` use the built-in HTTP API JWT
authorizer.

This is the current fit for ordinary authenticated routes where API Gateway can
enforce the authentication boundary before Lambda runs.

### Lambda request-authorized routes

Routes with `authorization_type = "CUSTOM"` use one declared Lambda request
authorizer from `var.request_authorizers`.

This keeps the module flexible enough to express mixed-mode routed behavior
without hardcoding RSVP-specific assumptions into the reusable module itself.

---

## Lambda Proxy Integration Model

This module uses HTTP API Lambda proxy integrations with payload format version
`2.0`.

That is intentional:

- the platform's current routed Lambda workloads already use the HTTP API proxy
  request/response shape
- JWT and Lambda authorizer context can flow through without custom mapping
- the integration layer stays simple and close to the real deployed backend

The module does not implement mapping templates, transformation layers, or
REST-API-style resource trees.

---

## Stage Operations Baseline

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

This gives the platform one reusable backend throttling baseline before the
later edge-delivery layer is introduced.

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

This keeps the module ready for later browser-based frontend traffic without
forcing CORS behavior into the current backend-only environment rollout.

---

## Input Validation Direction

This module intentionally validates its interface strictly so invalid route or
authorizer definitions fail early.

Examples of guarded behavior include:

- route keys must use the expected `METHOD /path` shape
- only the currently approved platform methods are accepted:
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

This keeps the reusable module precise enough to support the current routed API
contract safely without baking application-specific behavior into the module.

---

## Outputs

The module exposes the API, stage, authorizer, and route identifiers later
layers are most likely to need:

- API identifiers and invoke values
- stage name and stage invoke URL
- JWT authorizer ID
- Lambda request authorizer IDs
- route IDs and route keys

These outputs matter because later environment composition and validation work
often need stable API Gateway identifiers without depending on Terraform
resource internals directly.

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

---

## Out Of Scope

The following concerns intentionally remain outside this module:

- CloudFront
- WAF
- custom domains
- Route 53 DNS records
- API Gateway REST API resources
- API Gateway X-Ray tracing
- Lambda deployment packaging workflows
- Lambda log groups

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
