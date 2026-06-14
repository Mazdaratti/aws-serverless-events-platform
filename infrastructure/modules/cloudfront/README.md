# CloudFront Edge Delivery Module

This module manages the platform's CloudFront edge distribution.

It combines a private S3 frontend origin and an API Gateway backend origin
behind one public endpoint. The module is intentionally platform-shaped rather
than a general-purpose CloudFront abstraction.

## Resources And Behavior

The module creates:

- one CloudFront Origin Access Control for the S3 frontend origin
- one CloudFront Function for frontend SPA navigation rewrites
- one CloudFront distribution

That distribution is configured with:

- one private S3 frontend origin
- one API Gateway backend origin
- one default cache behavior for static frontend assets
- two ordered cache behaviors for the frontend application namespace:
  - `/app`
  - `/app/*`
- two ordered cache behaviors for the existing backend route family:
  - `/events`
  - `/events/*`
- HTTPS redirect at the edge
- AWS managed static-content caching policy
- AWS managed API no-cache policy
- AWS managed API origin request policy
- optional WAF Web ACL association
- default CloudFront certificate

It exposes the distribution, OAC, and SPA rewrite function identifiers required
by caller-owned integrations.

## Module Boundary

This module owns:

- the CloudFront distribution
- the S3 Origin Access Control
- static frontend and API cache behaviors
- the `/app` SPA rewrite function and association
- optional WAF Web ACL association

Callers remain responsible for:

- the private S3 origin bucket and its bucket policy
- the API Gateway origin
- the WAF Web ACL
- Route 53 records, custom domains, and ACM certificates
- logging buckets
- frontend assets, uploads, and cache invalidations

## S3 Origin Access Contract

This module uses CloudFront Origin Access Control for the S3 origin.

- OAC is the current CloudFront model for private S3 origins
- the frontend bucket is not a public website bucket
- CloudFront signs S3 origin requests with SigV4
- the legacy Origin Access Identity pattern is not used

OAC does not grant bucket access by itself. The caller must attach an S3 bucket
policy that permits the CloudFront service principal to read objects and scopes
that access to the module's `distribution_arn`.

## API Gateway Origin Contract

The API Gateway origin is modeled as a custom HTTPS origin.

The module expects:

- the API Gateway domain name without `https://`
- an optional API Gateway stage path such as `/dev`

CloudFront appends `api_origin_path` before forwarding requests to the API
Gateway origin.

For example:

- CloudFront viewer path:
  - `/events`
- `api_origin_path`:
  - `/dev`
- API Gateway receives:
  - `/dev/events`

This preserves the existing routed backend path contract while hiding the
stage-qualified execute-api shape from the long-term browser-facing product.

## API Route Contract

CloudFront forwards the platform's backend route family:

- `/events`
- `/events/*`

Using both `/events` and `/events/*` ensures that the exact collection path and
child resource paths are forwarded to API Gateway. The module does not
introduce an additional `/api/*` prefix.

## Frontend SPA Routing

Frontend application routes are reserved under:

- `/app`
- `/app/*`

These paths are served from the private S3 frontend origin.

The module attaches a CloudFront Function only to the `/app` and `/app/*`
behaviors. The function rewrites eligible browser HTML navigations to:

- `/index.html`

This supports React Router deep links and browser refreshes without using a
broad CloudFront 403/404 fallback.

Important:

- `/events` and `/events/*` are still forwarded to API Gateway
- API behaviors do not run the SPA rewrite function
- static asset requests under `/app/*` are not rewritten
- missing static assets still return real S3 or CloudFront errors

## Cache Behavior

The module intentionally separates frontend application, static asset, and API
behavior.

Static frontend behavior:

- uses the S3 origin
- allows `GET` and `HEAD`
- redirects HTTP to HTTPS
- enables compression
- uses AWS managed `Managed-CachingOptimized`

Frontend application behavior:

- matches `/app` and `/app/*`
- uses the S3 origin
- allows `GET` and `HEAD`
- redirects HTTP to HTTPS
- enables compression
- uses AWS managed `Managed-CachingOptimized`
- attaches the SPA rewrite CloudFront Function on viewer requests

API behavior:

- uses the API Gateway origin
- allows all methods needed by the platform's backend route family
- redirects HTTP to HTTPS
- enables compression
- uses AWS managed `Managed-CachingDisabled`
- uses AWS managed `Managed-AllViewerExceptHostHeader`

The no-cache API behavior is deliberate because the backend includes:

- authenticated reads
- mutating writes
- authorization-sensitive responses
- RSVP state changes

## WAF Association

The module supports optional WAF attachment through:

- `web_acl_arn`

The module does not create WAF resources. Callers may pass a CloudFront-scoped
WAF Web ACL ARN from a separately managed resource or module.

## Inputs

The module accepts:

- `name_prefix`
- `tags`
- `s3_origin_bucket_regional_domain_name`
- `s3_origin_id`
- `api_origin_domain_name`
- `api_origin_id`
- `api_origin_path`
- `web_acl_arn`
- `price_class`
- `enabled`
- `default_root_object`

## Outputs

The module exposes:

- `distribution_id`
- `distribution_arn`
- `distribution_domain_name`
- `distribution_hosted_zone_id`
- `s3_origin_access_control_id`
- `spa_rewrite_function_arn`
- `spa_rewrite_function_name`

The distribution ARN is especially important for caller-owned S3 bucket policy
wiring when using OAC.

## Example

This module includes a runnable example:

- `examples/basic_usage`

The example shows how to:

- define a small naming baseline
- define the baseline tag map
- create a minimal private S3 frontend origin
- create a minimal API Gateway HTTP API origin
- call the CloudFront module
- expose the SPA rewrite function for validation
- attach a caller-owned S3 bucket policy for OAC access

The example intentionally does not create WAF, Route 53 records, ACM
certificates, custom domains, frontend assets, logging buckets, or deployment
automation.

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | ~> 1.14.0 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | ~> 6.37 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_aws"></a> [aws](#provider\_aws) | 6.42.0 |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [aws_cloudfront_distribution.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_distribution) | resource |
| [aws_cloudfront_function.spa_rewrite](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_function) | resource |
| [aws_cloudfront_origin_access_control.s3](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_origin_access_control) | resource |
| [aws_cloudfront_cache_policy.api](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudfront_cache_policy) | data source |
| [aws_cloudfront_cache_policy.static](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudfront_cache_policy) | data source |
| [aws_cloudfront_origin_request_policy.api](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/cloudfront_origin_request_policy) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_api_origin_domain_name"></a> [api\_origin\_domain\_name](#input\_api\_origin\_domain\_name) | Domain name of the API Gateway origin, without protocol or stage path. | `string` | n/a | yes |
| <a name="input_api_origin_id"></a> [api\_origin\_id](#input\_api\_origin\_id) | Stable CloudFront origin ID used for the API Gateway backend origin. | `string` | `"api-gateway-origin"` | no |
| <a name="input_api_origin_path"></a> [api\_origin\_path](#input\_api\_origin\_path) | Optional API Gateway stage path that CloudFront appends before forwarding requests to the API origin. | `string` | `null` | no |
| <a name="input_default_root_object"></a> [default\_root\_object](#input\_default\_root\_object) | Default object CloudFront returns for requests to the distribution root. | `string` | `"index.html"` | no |
| <a name="input_enabled"></a> [enabled](#input\_enabled) | Whether the CloudFront distribution is enabled. | `bool` | `true` | no |
| <a name="input_name_prefix"></a> [name\_prefix](#input\_name\_prefix) | Shared environment naming prefix used to derive CloudFront distribution resource names. | `string` | n/a | yes |
| <a name="input_price_class"></a> [price\_class](#input\_price\_class) | CloudFront price class used to keep the first edge-delivery baseline cost-aware. | `string` | `"PriceClass_100"` | no |
| <a name="input_s3_origin_bucket_regional_domain_name"></a> [s3\_origin\_bucket\_regional\_domain\_name](#input\_s3\_origin\_bucket\_regional\_domain\_name) | Regional domain name of the private S3 bucket used as the frontend asset origin. | `string` | n/a | yes |
| <a name="input_s3_origin_id"></a> [s3\_origin\_id](#input\_s3\_origin\_id) | Stable CloudFront origin ID used for the private S3 frontend origin. | `string` | `"s3-frontend-origin"` | no |
| <a name="input_tags"></a> [tags](#input\_tags) | Baseline tags passed from the environment root and extended with resource-specific Name tags inside the module. | `map(string)` | n/a | yes |
| <a name="input_web_acl_arn"></a> [web\_acl\_arn](#input\_web\_acl\_arn) | Optional AWS WAFv2 Web ACL ARN to associate with the CloudFront distribution. | `string` | `null` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_distribution_arn"></a> [distribution\_arn](#output\_distribution\_arn) | ARN of the CloudFront distribution. |
| <a name="output_distribution_domain_name"></a> [distribution\_domain\_name](#output\_distribution\_domain\_name) | Domain name of the CloudFront distribution. |
| <a name="output_distribution_hosted_zone_id"></a> [distribution\_hosted\_zone\_id](#output\_distribution\_hosted\_zone\_id) | Route 53 hosted zone ID used by CloudFront distributions. |
| <a name="output_distribution_id"></a> [distribution\_id](#output\_distribution\_id) | ID of the CloudFront distribution. |
| <a name="output_s3_origin_access_control_id"></a> [s3\_origin\_access\_control\_id](#output\_s3\_origin\_access\_control\_id) | ID of the Origin Access Control used for the private S3 frontend origin. |
| <a name="output_spa_rewrite_function_arn"></a> [spa\_rewrite\_function\_arn](#output\_spa\_rewrite\_function\_arn) | ARN of the CloudFront Function that rewrites eligible /app SPA navigations. |
| <a name="output_spa_rewrite_function_name"></a> [spa\_rewrite\_function\_name](#output\_spa\_rewrite\_function\_name) | Name of the CloudFront Function that rewrites eligible /app SPA navigations. |
<!-- END_TF_DOCS -->
