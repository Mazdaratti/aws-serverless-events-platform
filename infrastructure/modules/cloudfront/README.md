# CloudFront Edge Distribution Baseline

This module creates the reusable CloudFront distribution baseline for the
serverless events platform's edge-delivery layer.

It is intentionally platform-specific. The goal is not to provide a generic
CloudFront abstraction or a broad CDN factory. Instead, this module defines the
concrete public edge distribution shape that the private S3 frontend origin,
API Gateway backend origin, and WAF baseline will compose around.

This module is CloudFront-distribution-only in v1.

---

## What This Module Creates

This module currently creates:

- one CloudFront Origin Access Control for the S3 frontend origin
- one CloudFront distribution

That distribution is configured with:

- one private S3 frontend origin
- one API Gateway backend origin
- one default cache behavior for static frontend assets
- two ordered cache behaviors for the existing backend route family:
  - `/events`
  - `/events/*`
- HTTPS redirect at the edge
- AWS managed static-content caching policy
- AWS managed API no-cache policy
- AWS managed API origin request policy
- optional WAF Web ACL association
- default CloudFront certificate

It also exposes the distribution and OAC identifiers later layers are most
likely to need.

---

## Why This Module Stays CloudFront-Focused

This step is focused on the reusable edge distribution baseline the platform
clearly needs after creating the private S3 origin bucket and WAF baseline:

- one CloudFront distribution
- private S3 frontend delivery through OAC
- API Gateway origin forwarding
- static and API behavior separation
- optional Web ACL attachment point

The module does not create S3 buckets, S3 bucket policies, WAF Web ACLs, Route
53 records, ACM certificates, custom domains, logging buckets, frontend assets,
or deployment automation. Those concerns either already belong to other modules
or are intentionally deferred to later milestones.

Keeping the module limited to CloudFront distribution behavior makes the design
easier to understand and keeps `envs/dev` composition-focused.

---

## Origin Access Control Direction

This module uses CloudFront Origin Access Control for the S3 origin.

That is intentional:

- OAC is the current CloudFront model for private S3 origins
- the frontend bucket is not a public website bucket
- CloudFront signs S3 origin requests with SigV4
- the legacy Origin Access Identity pattern is not used

Important:

OAC alone is not enough to grant CloudFront access to the S3 bucket.

The caller must also attach a bucket policy that allows the CloudFront service
principal to read objects from the bucket, usually scoped with:

- the CloudFront distribution ARN
- an `AWS:SourceArn` condition

That bucket policy remains outside this module because bucket ownership belongs
to the caller or environment composition layer.

---

## API Gateway Origin Direction

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

---

## Backend Route Shape

The current platform direction intentionally does not introduce `/api/*` in
this phase.

Instead, CloudFront forwards the existing backend route family:

- `/events`
- `/events/*`

This aligns the edge layer with the routes already implemented and validated in
API Gateway:

- `GET /events`
- `GET /events/mine`
- `GET /events/{event_id}`
- `POST /events`
- `PATCH /events/{event_id}`
- `POST /events/{event_id}/cancel`
- `POST /events/{event_id}/rsvp`
- `GET /events/{event_id}/rsvps`

Using both `/events` and `/events/*` avoids missing the exact list/create path
while still forwarding child event paths to API Gateway.

---

## Cache Behavior Direction

The module intentionally separates static and API behavior.

Static frontend behavior:

- uses the S3 origin
- allows `GET` and `HEAD`
- redirects HTTP to HTTPS
- enables compression
- uses AWS managed `Managed-CachingOptimized`

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

---

## WAF Association Direction

The module supports optional WAF attachment through:

- `web_acl_arn`

The module does not create WAF resources. The reusable WAF baseline belongs to
the separate `waf` module, and environment roots can pass its Web ACL ARN into
this module when they are ready to attach protection at the CloudFront edge.

---

## Inputs

This module keeps its public input surface intentionally small:

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

This gives environment roots enough control to compose the edge distribution
without turning the module into a broad CloudFront framework.

---

## Outputs

The module exposes the values later layers are most likely to need:

- `distribution_id`
- `distribution_arn`
- `distribution_domain_name`
- `distribution_hosted_zone_id`
- `s3_origin_access_control_id`

The distribution ARN is especially important for caller-owned S3 bucket policy
wiring when using OAC.

---

## Example

This module includes a runnable example:

- `examples/basic_usage`

The example shows how to:

- define a small naming baseline
- define the baseline tag map
- create a minimal private S3 frontend origin
- create a minimal API Gateway HTTP API origin
- call the CloudFront module
- attach a caller-owned S3 bucket policy for OAC access

The example intentionally does not create WAF, Route 53 records, ACM
certificates, custom domains, frontend assets, logging buckets, or deployment
automation.

---

## Out Of Scope

The following concerns intentionally remain outside this module:

- S3 bucket creation
- S3 bucket policy ownership
- WAF Web ACL creation
- Route 53 DNS records
- ACM certificates
- custom domains
- CloudFront logging buckets
- frontend application assets
- frontend deployment automation
- SPA routing and custom error rewrites

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
| <a name="provider_aws"></a> [aws](#provider\_aws) | 6.42.0 |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [aws_cloudfront_distribution.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudfront_distribution) | resource |
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
<!-- END_TF_DOCS -->
