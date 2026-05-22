# Remote Backend Baseline

This module creates a reusable S3 bucket baseline for Terraform remote state.

It is intentionally focused on the persistent backend bucket only. The module
does not write `backend.tf`, does not migrate local state, and does not create
GitHub OIDC roles or deployment workflow permissions.

Those concerns belong to environment bootstrap roots and migration runbooks.

---

## What This Module Creates

This module currently creates:

- one S3 bucket for Terraform state
- one bucket versioning configuration
- one bucket default server-side encryption configuration using SSE-S3
- one bucket public access block configuration
- one bucket ownership-controls configuration using `BucketOwnerEnforced`

It also exposes the core bucket identifiers later bootstrap or environment
layers are most likely to need:

- state bucket name
- state bucket ARN
- state bucket regional domain name

This keeps the reusable backend baseline small, reviewable, and separate from
environment-specific backend migration work.

---

## Persistent Backend Direction

This module is designed for persistent Terraform state backends.

The state bucket uses:

- versioning enabled
- default encryption at rest
- public access blocked
- ACL-free bucket ownership behavior
- Terraform `prevent_destroy = true`

The `prevent_destroy` setting is deliberate. Terraform lifecycle settings must
be literal values, so this module does not expose a toggle for switching between
persistent and teardown-friendly behavior.

For short-lived `dev` bootstrap flows, use a dedicated bootstrap root that owns
its backend bucket directly. That keeps the reusable module suitable for
longer-lived environments while allowing `dev` bootstrap infrastructure to be
destroyed and recreated when needed.

---

## Backend Configuration Boundary

This module creates the backend bucket infrastructure only.

It does not create:

- `backend.tf`
- Terraform backend key conventions
- GitHub OIDC providers
- GitHub Actions IAM roles
- state migration commands
- deployment workflows

That split is intentional:

- the bucket is reusable infrastructure
- backend key paths are environment-specific
- backend config generation belongs to bootstrap
- state migration is an operator action that should be validated separately

For this project, the `dev` environment uses `infrastructure/bootstrap/dev` to
create a teardown-friendly backend bucket directly and generate the environment
backend configuration.

Persistent environment bootstrap roots should use this module instead. For
example, a production bootstrap root such as `infrastructure/bootstrap/prod`
could compose `infrastructure/modules/remote_backend` for the state bucket, then
own production-specific backend config generation, state migration instructions,
and GitHub OIDC deployment permissions separately.

---

## Naming

Callers can either:

- pass `state_bucket_name` explicitly
- or let the module derive a bucket name from `name_prefix` plus a random suffix

The derived name shape is:

```text
<name_prefix>-tf-state-<random suffix>
```

S3 bucket names are globally unique. The random suffix keeps the default path
usable across accounts without asking every caller to invent a unique name
before trying the module.

When `state_bucket_name` is provided, the module validates the value against
the current S3 general purpose bucket naming rules, including reserved prefixes
and suffixes.

---

## Examples

This module includes two runnable examples:

- `examples/basic_usage`
- `examples/custom_bucket_name`

The basic example lets the module derive the state bucket name.

The custom bucket example shows how a caller can provide an explicit bucket
name for a persistent environment that follows an account or organization naming
standard.

Both examples create real S3 resources if applied. They are validation-oriented
and should be reviewed before use in a real account.

---

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | ~> 1.14.0 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | ~> 6.37 |
| <a name="requirement_random"></a> [random](#requirement\_random) | ~> 3.8 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_aws"></a> [aws](#provider\_aws) | 6.45.0 |
| <a name="provider_random"></a> [random](#provider\_random) | 3.9.0 |



## Resources

| Name | Type |
|------|------|
| [aws_s3_bucket.terraform_state](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket) | resource |
| [aws_s3_bucket_ownership_controls.terraform_state](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_ownership_controls) | resource |
| [aws_s3_bucket_public_access_block.terraform_state](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_public_access_block) | resource |
| [aws_s3_bucket_server_side_encryption_configuration.terraform_state](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_server_side_encryption_configuration) | resource |
| [aws_s3_bucket_versioning.terraform_state](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_versioning) | resource |
| [random_id.bucket_suffix](https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/id) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_name_prefix"></a> [name\_prefix](#input\_name\_prefix) | Shared environment naming prefix used to derive the Terraform state bucket name when state\_bucket\_name is not set. | `string` | n/a | yes |
| <a name="input_tags"></a> [tags](#input\_tags) | Baseline tags passed from the environment root and extended with resource-specific Name tags inside the module. | `map(string)` | n/a | yes |
| <a name="input_state_bucket_name"></a> [state\_bucket\_name](#input\_state\_bucket\_name) | Optional explicit globally unique S3 bucket name for Terraform state. When null, the module derives a name from name\_prefix and a random suffix. | `string` | `null` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_state_bucket_arn"></a> [state\_bucket\_arn](#output\_state\_bucket\_arn) | ARN of the S3 bucket created for Terraform state. |
| <a name="output_state_bucket_name"></a> [state\_bucket\_name](#output\_state\_bucket\_name) | Name of the S3 bucket created for Terraform state. |
| <a name="output_state_bucket_regional_domain_name"></a> [state\_bucket\_regional\_domain\_name](#output\_state\_bucket\_regional\_domain\_name) | Regional domain name of the S3 bucket created for Terraform state. |
<!-- END_TF_DOCS -->
