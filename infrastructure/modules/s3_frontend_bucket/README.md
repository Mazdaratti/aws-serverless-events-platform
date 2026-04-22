# S3 Frontend Origin Bucket Baseline

This module creates the initial private S3 frontend-origin bucket baseline for
the serverless events platform.

It is intentionally platform-specific. The goal is not to provide a generic S3
abstraction or a broad bucket factory. Instead, this module defines the
concrete private bucket baseline that the later CloudFront delivery layer will
depend on.

This module manages origin-bucket infrastructure only.

---

## What This Module Creates

This module currently creates:

- one private S3 bucket
- one bucket-level public access block configuration
- one bucket ownership-controls configuration
- one bucket default server-side encryption configuration
- one bucket versioning configuration

It also exposes the core bucket identifiers later layers are most likely to
need, including:

- the bucket ARN
- the bucket name
- the bucket ID
- the bucket regional domain name

This keeps the first edge-storage implementation small, reviewable, and aligned
with the platform's locked edge-delivery direction.

---

## Why This Module Stays Origin-Bucket-Focused

This step is focused on the private S3 bucket baseline the platform clearly
needs before CloudFront wiring can be added:

- private object storage for frontend assets
- direct-public-access blocking
- modern bucket ownership controls
- default encryption at rest
- optional versioning

The module does not create CloudFront distributions, origin access control,
bucket policies coupled to CloudFront, website hosting configuration, Route 53
records, ACM certificates, logging buckets, replication, lifecycle transitions,
or object upload automation. Those concerns may become relevant later, but they
are intentionally outside the scope of this first frontend-origin bucket step.

Keeping the module limited to the origin bucket baseline makes the design
easier to understand and avoids baking future CloudFront assumptions into the
bucket module too early.

---

## Private Origin Direction

This module is aligned with the platform's locked frontend-delivery direction:

- frontend assets are stored in S3
- the bucket stays private
- direct S3 website hosting is not used
- CloudFront will later become the intended public entry point

That means this module creates a bucket for origin storage, not for public
website delivery.

This is why the module:

- blocks all direct public access
- does not enable website hosting mode
- does not expose website endpoint outputs
- does not attach a CloudFront-specific bucket policy yet

---

## Key Design Decisions

### Public access is blocked at the bucket baseline

The module applies S3 bucket-level public access block settings directly.

That is intentional:

- the bucket is not meant to be browsed publicly
- later public delivery should flow through CloudFront instead
- the bucket baseline should already reflect the intended production shape

### Ownership controls use BucketOwnerEnforced

The module uses the modern `BucketOwnerEnforced` ownership model.

That keeps the private origin bucket on the simpler ACL-free path and avoids
introducing unnecessary ACL behavior for this baseline.

### SSE-S3 is the encryption baseline

The module enables default SSE-S3 encryption with `AES256`.

That is intentional:

- encryption at rest should be enabled by default
- this step does not yet need customer-managed KMS keys
- SSE-S3 keeps the baseline secure while staying cost-aware and small

### Versioning is configurable

Versioning is exposed as a small boolean input rather than hardcoded on or off.

That allows environment wiring to decide whether this bucket should keep object
history without turning the module into a broad policy surface.

---

## Inputs

This module keeps its public input surface intentionally small:

- `name_prefix`
- `bucket_name_suffix`
- `tags`
- `versioning_enabled`
- `force_destroy`

This keeps naming and tagging aligned with the environment root while leaving a
small amount of environment-level control over destruction and versioning.

---

## Outputs

The module exposes the bucket values later layers are most likely to need:

- `bucket_arn`
- `bucket_id`
- `bucket_name`
- `bucket_regional_domain_name`

The regional domain name is especially important because later CloudFront
origin wiring is more likely to depend on that value than on website-style S3
endpoints.

---

## Example

This module includes a runnable example:

- `examples/basic_usage`

The example shows how to:

- define a small naming baseline
- define the baseline tag map
- configure the AWS provider for `eu-central-1`
- call the module with the intended private-origin input shape
- enable versioning in the example so the full bucket baseline is visible

The example intentionally does not create CloudFront, WAF, Route 53, ACM, or
frontend assets.

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
| <a name="provider_aws"></a> [aws](#provider\_aws) | ~> 6.37 |

## Modules

No modules.

## Resources

| Name | Type |
|------|------|
| [aws_s3_bucket.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket) | resource |
| [aws_s3_bucket_ownership_controls.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_ownership_controls) | resource |
| [aws_s3_bucket_public_access_block.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_public_access_block) | resource |
| [aws_s3_bucket_server_side_encryption_configuration.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_server_side_encryption_configuration) | resource |
| [aws_s3_bucket_versioning.this](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_versioning) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_bucket_name_suffix"></a> [bucket\_name\_suffix](#input\_bucket\_name\_suffix) | Suffix appended to name\_prefix when rendering the private frontend origin bucket name. | `string` | `"frontend"` | no |
| <a name="input_force_destroy"></a> [force\_destroy](#input\_force\_destroy) | Whether Terraform may destroy the frontend origin bucket even when it still contains objects. | `bool` | `false` | no |
| <a name="input_name_prefix"></a> [name\_prefix](#input\_name\_prefix) | Shared environment naming prefix used to derive the frontend origin bucket name. | `string` | n/a | yes |
| <a name="input_tags"></a> [tags](#input\_tags) | Baseline tags passed from the environment root and extended with resource-specific Name tags inside the module. | `map(string)` | n/a | yes |
| <a name="input_versioning_enabled"></a> [versioning\_enabled](#input\_versioning\_enabled) | Whether S3 bucket versioning is enabled for the private frontend origin bucket. | `bool` | `false` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_bucket_arn"></a> [bucket\_arn](#output\_bucket\_arn) | ARN of the private frontend origin bucket. |
| <a name="output_bucket_id"></a> [bucket\_id](#output\_bucket\_id) | ID of the private frontend origin bucket. |
| <a name="output_bucket_name"></a> [bucket\_name](#output\_bucket\_name) | Name of the private frontend origin bucket. |
| <a name="output_bucket_regional_domain_name"></a> [bucket\_regional\_domain\_name](#output\_bucket\_regional\_domain\_name) | Regional domain name of the private frontend origin bucket. |
<!-- END_TF_DOCS -->
