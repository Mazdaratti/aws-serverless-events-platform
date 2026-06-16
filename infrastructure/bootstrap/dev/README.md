# Dev Bootstrap: Remote State and GitHub OIDC

This bootstrap root creates the `dev` foundation for remote Terraform state and
GitHub Actions AWS authentication.

It is intentionally separate from `infrastructure/envs/dev`.

The [`dev` environment root](../../envs/dev/README.md) owns the application
platform. This bootstrap root owns only the resources required before that
environment can use remote state and GitHub Actions can authenticate to AWS
without long-lived credentials.

The complete bootstrap, input-sync, and provisioning sequence is documented in
the [project setup guide](../../../docs/project-setup.md).

---

## What This Root Creates

This root creates:

- one teardown-friendly S3 bucket for `dev` Terraform state
- S3 bucket versioning
- S3 default server-side encryption using SSE-S3
- S3 public access block settings
- S3 ownership controls using `BucketOwnerEnforced`
- generated S3 backend configuration for `infrastructure/envs/dev`
- one GitHub Actions OIDC provider
- one branch-scoped GitHub Actions IAM role
- one Terraform state access policy
- split deployment policies for Terraform provisioning and artifact deployment
- one repo-aligned permissions boundary for the GitHub Actions role

The generated backend config uses the Terraform S3 backend with native S3
lockfile support:

```hcl
use_lockfile = true
```

This project uses S3 native lockfiles for the `dev` backend baseline. It does
not create a DynamoDB lock table.

---

## What This Root Does Not Do

This root does not:

- migrate existing `infrastructure/envs/dev` state to S3
- run `terraform init -migrate-state`
- create GitHub Actions workflow files
- run application deployment workflows
- deploy Lambda ZIP files
- deploy frontend artifacts
- create SNS alert subscriptions
- change Lambda, API Gateway, SQS, EventBridge, SES, Cognito, CloudFront, or
  WAF runtime behavior

Initializing or migrating the environment root against the generated backend
remains a separate, explicit operation after bootstrap succeeds.

---

## Remote State Bucket

The state bucket is owned directly by this `dev` bootstrap root instead of the
reusable [`remote_backend` module](../../modules/remote_backend/README.md).

That is deliberate.

The reusable module is persistent and uses Terraform `prevent_destroy = true`.
This bootstrap root is `dev`-oriented and teardown-friendly, so the bucket uses:

```hcl
force_destroy = true
```

The bucket still keeps the important state protections:

- versioning enabled
- default encryption at rest
- public access blocked
- ACL-free ownership with `BucketOwnerEnforced`

The bucket name is derived from:

```text
<project_name>-<environment>-tf-state-<random suffix>
```

Callers can pass `state_bucket_name` to use an explicit bucket name instead.

---

## Generated Backend Config

This root writes:

```text
infrastructure/envs/dev/backend.tf
```

The generated file is ignored by Git.

The backend key is stable and environment-specific:

```text
infrastructure/envs/dev/terraform.tfstate
```

Generating this file keeps the environment backend aligned with the bucket
created by this root. Terraform initialization and any required state migration
remain separate reviewed operations.

---

## GitHub OIDC Trust

This root creates one IAM OIDC provider for:

```text
token.actions.githubusercontent.com
```

The GitHub Actions role trust policy is scoped to:

- GitHub organization: `github_org`
- GitHub repository: `github_repo`
- Git branch: `github_branch`
- OIDC audience: `sts.amazonaws.com`

For this project, the validated `dev` trust subject is:

```text
repo:Mazdaratti/aws-serverless-events-platform:ref:refs/heads/main
```

The current AWS workflows run manually from `main` and use this branch-scoped
subject. GitHub Environment subjects are not part of the current trust policy.

---

## IAM Policy Shape

The GitHub Actions role has separate managed policies for state access and
deployment access.

State access is intentionally small and limited to:

- reading/listing the backend bucket
- reading and writing the `dev` state object
- reading, writing, and deleting the S3 `.tflock` lockfile

Deployment access is split into smaller managed policies for:

- core platform resources:
  - DynamoDB
  - SQS
  - EventBridge
  - SNS
  - SES
  - Cognito
- compute and observability resources:
  - Lambda
  - CloudWatch Logs
  - CloudWatch alarms and dashboards
  - API Gateway
- edge and storage resources:
  - S3
  - CloudFront
  - WAFv2
- runtime IAM resources:
  - project-scoped Lambda roles and policies
  - `iam:PassRole` scoped to project Lambda roles

The split keeps the policies within IAM managed policy size limits and makes the
permission groups easier to review.

These policies support the manual provisioning, Lambda code deployment, and
frontend deployment workflows. The bootstrap root creates the AWS permissions;
it does not run those workflows or deploy application artifacts.

When enabled, the permissions boundary limits the maximum permissions available
to the GitHub Actions role. It does not grant permissions by itself; access is
granted by the attached state and deployment policies.

---

## Validation Status

The bootstrap root has been validated in AWS for `dev`.

Validation confirmed:

- the backend bucket was created with versioning, SSE-S3 encryption, public
  access block, and `BucketOwnerEnforced`
- `backend.tf` was generated and remains untracked because it is ignored by Git
- the GitHub OIDC provider uses the expected provider URL, audience, and
  thumbprint
- the GitHub Actions role trust is scoped to the repository and `main` branch
- the GitHub Actions role has the state policy, split deploy policies, and
  permissions boundary in place
- the branch-scoped role can be assumed through the manual AWS OIDC smoke
  workflow
- a post-apply Terraform plan is clean

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | ~> 1.14.0 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | ~> 6.37 |
| <a name="requirement_local"></a> [local](#requirement\_local) | ~> 2.5 |
| <a name="requirement_random"></a> [random](#requirement\_random) | ~> 3.8 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_aws"></a> [aws](#provider\_aws) | 6.46.0 |
| <a name="provider_local"></a> [local](#provider\_local) | 2.9.0 |
| <a name="provider_random"></a> [random](#provider\_random) | 3.9.0 |



## Resources

| Name | Type |
|------|------|
| [aws_iam_openid_connect_provider.github](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_openid_connect_provider) | resource |
| [aws_iam_policy.github_actions_boundary](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_policy) | resource |
| [aws_iam_policy.github_actions_deploy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_policy) | resource |
| [aws_iam_policy.github_actions_deploy_compute_observability](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_policy) | resource |
| [aws_iam_policy.github_actions_deploy_edge_storage](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_policy) | resource |
| [aws_iam_policy.github_actions_deploy_iam](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_policy) | resource |
| [aws_iam_policy.github_actions_state](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_policy) | resource |
| [aws_iam_role.github_actions](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role) | resource |
| [aws_iam_role_policy_attachment.github_actions_deploy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy_attachment) | resource |
| [aws_iam_role_policy_attachment.github_actions_deploy_compute_observability](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy_attachment) | resource |
| [aws_iam_role_policy_attachment.github_actions_deploy_edge_storage](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy_attachment) | resource |
| [aws_iam_role_policy_attachment.github_actions_deploy_iam](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy_attachment) | resource |
| [aws_iam_role_policy_attachment.github_actions_state](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy_attachment) | resource |
| [aws_s3_bucket.terraform_state](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket) | resource |
| [aws_s3_bucket_ownership_controls.terraform_state](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_ownership_controls) | resource |
| [aws_s3_bucket_public_access_block.terraform_state](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_public_access_block) | resource |
| [aws_s3_bucket_server_side_encryption_configuration.terraform_state](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_server_side_encryption_configuration) | resource |
| [aws_s3_bucket_versioning.terraform_state](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_versioning) | resource |
| [local_file.backend_config](https://registry.terraform.io/providers/hashicorp/local/latest/docs/resources/file) | resource |
| [random_id.bucket_suffix](https://registry.terraform.io/providers/hashicorp/random/latest/docs/resources/id) | resource |
| [aws_iam_policy_document.github_actions_deploy_compute_observability_permissions](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_iam_policy_document.github_actions_deploy_core_permissions](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_iam_policy_document.github_actions_deploy_edge_storage_permissions](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_iam_policy_document.github_actions_deploy_iam_permissions](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_iam_policy_document.github_actions_state_permissions](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_iam_policy_document.github_assume_role](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_github_org"></a> [github\_org](#input\_github\_org) | GitHub organization or user name that owns the repository allowed to assume the bootstrap-created OIDC role. | `string` | n/a | yes |
| <a name="input_github_repo"></a> [github\_repo](#input\_github\_repo) | GitHub repository name allowed to assume the bootstrap-created OIDC role. | `string` | n/a | yes |
| <a name="input_project_name"></a> [project\_name](#input\_project\_name) | Project name used as the shared naming and tagging baseline for dev bootstrap resources. | `string` | n/a | yes |
| <a name="input_additional_tags"></a> [additional\_tags](#input\_additional\_tags) | Additional tags merged into the bootstrap provider default tags. | `map(string)` | `{}` | no |
| <a name="input_aws_region"></a> [aws\_region](#input\_aws\_region) | AWS region where dev bootstrap resources are created. | `string` | `"eu-central-1"` | no |
| <a name="input_create_permissions_boundary"></a> [create\_permissions\_boundary](#input\_create\_permissions\_boundary) | Whether to create and attach the repo-aligned permissions boundary to the GitHub Actions OIDC role. | `bool` | `true` | no |
| <a name="input_environment"></a> [environment](#input\_environment) | Environment name used for dev bootstrap resource naming and the generated backend configuration. | `string` | `"dev"` | no |
| <a name="input_github_branch"></a> [github\_branch](#input\_github\_branch) | GitHub branch name allowed to assume the bootstrap-created OIDC role. | `string` | `"main"` | no |
| <a name="input_state_bucket_name"></a> [state\_bucket\_name](#input\_state\_bucket\_name) | Optional explicit globally unique S3 bucket name for dev Terraform state. When null, bootstrap derives a name from the environment prefix and a random suffix. | `string` | `null` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_github_actions_deploy_policy_arn"></a> [github\_actions\_deploy\_policy\_arn](#output\_github\_actions\_deploy\_policy\_arn) | ARN of the primary IAM policy granting GitHub Actions core Terraform deployment permissions for dev. |
| <a name="output_github_actions_deploy_policy_arns"></a> [github\_actions\_deploy\_policy\_arns](#output\_github\_actions\_deploy\_policy\_arns) | ARNs of the IAM policies granting GitHub Actions scoped Terraform deployment permissions for dev. |
| <a name="output_github_actions_permissions_boundary_policy_arn"></a> [github\_actions\_permissions\_boundary\_policy\_arn](#output\_github\_actions\_permissions\_boundary\_policy\_arn) | ARN of the optional GitHub Actions permissions boundary policy, or null when disabled. |
| <a name="output_github_actions_role_arn"></a> [github\_actions\_role\_arn](#output\_github\_actions\_role\_arn) | ARN of the GitHub Actions OIDC role. |
| <a name="output_github_actions_role_name"></a> [github\_actions\_role\_name](#output\_github\_actions\_role\_name) | Name of the GitHub Actions OIDC role. |
| <a name="output_github_actions_state_policy_arn"></a> [github\_actions\_state\_policy\_arn](#output\_github\_actions\_state\_policy\_arn) | ARN of the IAM policy granting GitHub Actions access to the dev Terraform state backend. |
| <a name="output_github_oidc_provider_arn"></a> [github\_oidc\_provider\_arn](#output\_github\_oidc\_provider\_arn) | ARN of the GitHub Actions OIDC provider. |
| <a name="output_state_backend_key"></a> [state\_backend\_key](#output\_state\_backend\_key) | S3 object key used by the generated dev Terraform backend configuration. |
| <a name="output_state_bucket_arn"></a> [state\_bucket\_arn](#output\_state\_bucket\_arn) | ARN of the S3 bucket created for dev Terraform state. |
| <a name="output_state_bucket_name"></a> [state\_bucket\_name](#output\_state\_bucket\_name) | Name of the S3 bucket created for dev Terraform state. |
<!-- END_TF_DOCS -->
