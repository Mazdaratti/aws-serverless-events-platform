# S3 Frontend Origin Module

This module creates a private S3 origin bucket for frontend assets in
the serverless events platform.

It is intentionally platform-specific rather than a generic bucket factory.
The module owns the bucket and its storage-level security controls.

Each environment root composes the bucket with its CloudFront distribution,
origin access policy, and frontend deployment process. The platform-wide edge
delivery model is documented in the
[architecture guide](../../../docs/architecture.md).

---

## What This Module Creates

This module creates:

- one private S3 bucket
- one bucket-level public access block configuration
- one bucket ownership-controls configuration
- one bucket default server-side encryption configuration
- one bucket versioning configuration

It exposes:

- the bucket ARN
- the bucket name
- the bucket ID
- the bucket regional domain name

The caller controls the bucket-name suffix, versioning, destruction behavior,
shared naming, and tags.

---

## Module Boundary

The module owns:

- private bucket creation and naming
- public access block settings
- ACL-free ownership controls
- default SSE-S3 encryption
- configurable versioning and destruction behavior
- bucket outputs

It does not own:

- CloudFront distributions or origin access controls
- bucket policies that authorize a concrete distribution
- website hosting configuration
- Route 53 records or ACM certificates
- access-log buckets, replication, or lifecycle transitions
- frontend builds or object deployment

Those responsibilities belong to callers, edge-delivery modules, or deployment
automation.

---

## Private Origin Contract

The bucket is designed for private origin storage:

- frontend assets are stored in S3
- the bucket stays private
- direct S3 website hosting is not used
- public delivery is delegated to a caller-owned edge layer

That means this module creates a bucket for origin storage, not for public
website delivery.

This is why the module:

- blocks all direct public access
- does not enable website hosting mode
- does not expose website endpoint outputs
- does not attach a distribution-specific bucket policy

---

## Key Design Decisions

### Public access is blocked at the bucket baseline

The module applies S3 bucket-level public access block settings directly.

That is intentional:

- the bucket is not meant to be browsed publicly
- public delivery should flow through a controlled edge layer
- private access is enforced independently of caller composition

### Ownership controls use BucketOwnerEnforced

The module uses the modern `BucketOwnerEnforced` ownership model.

That keeps the private origin bucket on the simpler ACL-free path and avoids
introducing unnecessary ACL behavior for this baseline.

### SSE-S3 is the encryption baseline

The module enables default SSE-S3 encryption with `AES256`.

That is intentional:

- encryption at rest should be enabled by default
- the module does not introduce customer-managed KMS key ownership
- SSE-S3 keeps the storage contract small and cost-aware

### Versioning is configurable

Versioning is exposed as a small boolean input rather than hardcoded on or off.

That allows callers to choose whether the bucket keeps object history without
turning the module into a broad policy surface.

---

## Inputs

This module keeps its public input surface intentionally small:

- `name_prefix`
- `bucket_name_suffix`
- `tags`
- `versioning_enabled`
- `force_destroy`

This keeps naming and tagging aligned with the composing root while preserving
explicit caller control over destruction and versioning.

---

## Outputs

The module exposes:

- `bucket_arn`
- `bucket_id`
- `bucket_name`
- `bucket_regional_domain_name`

The regional domain name allows callers to configure an S3 origin without
enabling website hosting.

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

Applying the example creates a real S3 bucket and should be reviewed before use
in an AWS account.

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
