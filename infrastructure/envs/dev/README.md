# Development Environment (`envs/dev`)

This folder contains the Terraform root module for the local-first `dev` environment.

The root module stays intentionally thin and composition-focused.
It defines shared Terraform, provider, naming, and tagging baselines
and wires reusable infrastructure modules as the platform is implemented step by step.

---

## What This Environment Does Right Now

The current `dev` root module is responsible for:

- defining Terraform and AWS provider version constraints
- configuring the AWS provider for the selected region
- establishing shared environment naming and baseline tags
- declaring the required input values for local use
- composing reusable infrastructure modules for the dev environment

This keeps the environment root clean and composition-only while the platform is implemented step by step.

---

## Why Local State Is Used Here

This repository is currently in the local-state-first phase of the roadmap.

That means:

- Terraform state is kept locally during this stage
- remote backend setup is intentionally deferred to a later implementation step
- the environment root stays easier to understand while the platform foundation is still being built

This is a deliberate tradeoff for early development simplicity, not a production end state.

---

## How To Use This Environment

### 1. Create your local tfvars file

Use the example file as your starting point:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Then review and adjust:

- `project_name`
- `environment`
- `aws_region`

### 2. Initialize Terraform

```bash
terraform init
```

### 3. Review the plan

```bash
terraform plan
```

The plan will show the creation of real AWS resources from wired modules.

The plan is useful to:

- validate provider authentication
- validate variable wiring
- validate the dependency lock file
- validate the evaluation graph for the environment root
- validate real env/module composition before apply

---

## File Overview

- `versions.tf` keeps the Terraform CLI and AWS provider version baseline in one place
- `locals.tf` defines shared naming and tagging values for future module composition
- `variables.tf` declares the required environment inputs and validates that they are not empty
- `providers.tf` configures the AWS provider and applies baseline default tags
- `main.tf` composes the reusable modules for the dev environment
- `outputs.tf` re-exports outputs needed by later layers
- `terraform.tfvars.example` shows the required local input shape for this environment

---

## What This Environment Deploys

The dev environment is composed of reusable modules.

Each section below corresponds to **one module block in `main.tf`**.

New infrastructure is added by appending additional module blocks to `main.tf`.

---

## DynamoDB Data Layer

Creates the initial DynamoDB business data baseline for the platform.

Implemented via:

- `modules/dynamodb_data_layer`

This environment currently wires in:

- the `events` table for canonical event records
- the `rsvps` table for canonical RSVP membership records
- the first approved GSIs on the `events` table for future query-based listing patterns

Why this module is wired first:

- the platform needs a durable business data layer before API and compute layers can be composed above it
- the DynamoDB design establishes the canonical write model for events and RSVPs
- later IAM, Lambda, and API wiring will consume the table names and ARNs exported here

Important design notes:

- the primary RSVP business write remains synchronous through DynamoDB durable commit
- asynchronous services such as SQS are reserved for downstream side effects after commit
- the `rsvps` table is the source of truth for attendance membership
- event-level counters are helper fields, not the source of truth

The environment should stay thin:

- reusable AWS resource logic belongs in modules
- `envs/dev` should focus on composition and environment-level identity and placement inputs

Validation evidence for this milestone is documented in:

- `docs/validation/dynamodb-milestone.md`

---

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | ~> 1.14.0 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | ~> 6.37 |



## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_dynamodb_data_layer"></a> [dynamodb\_data\_layer](#module\_dynamodb\_data\_layer) | ../../modules/dynamodb_data_layer | n/a |



## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_aws_region"></a> [aws\_region](#input\_aws\_region) | AWS region where resources will be deployed. | `string` | n/a | yes |
| <a name="input_environment"></a> [environment](#input\_environment) | Deployment environment name. | `string` | n/a | yes |
| <a name="input_project_name"></a> [project\_name](#input\_project\_name) | Project name used for naming and tagging resources. | `string` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_events_table_arn"></a> [events\_table\_arn](#output\_events\_table\_arn) | ARN of the DynamoDB events table created for the dev environment. |
| <a name="output_events_table_name"></a> [events\_table\_name](#output\_events\_table\_name) | Name of the DynamoDB events table created for the dev environment. |
| <a name="output_rsvps_table_arn"></a> [rsvps\_table\_arn](#output\_rsvps\_table\_arn) | ARN of the DynamoDB RSVP table created for the dev environment. |
| <a name="output_rsvps_table_name"></a> [rsvps\_table\_name](#output\_rsvps\_table\_name) | Name of the DynamoDB RSVP table created for the dev environment. |
<!-- END_TF_DOCS -->
