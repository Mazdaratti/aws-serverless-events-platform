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
- point-in-time recovery is disabled by default in `dev` to reduce always-on non-production cost
- the reusable module still supports PITR, but this environment now treats it as an explicit environment-level behavior choice

The environment should stay thin:

- reusable AWS resource logic belongs in modules
- `envs/dev` should focus on composition and environment-level identity and placement inputs

Validation:

- validated via `terraform apply`, AWS inspection, and a clean post-apply `terraform plan`
- confirmed table creation, approved GSIs, `PAY_PER_REQUEST`, and table class `STANDARD`
- `dev` now defaults point-in-time recovery to disabled as a cost-saving environment override
- optional CLI data validation was also completed
- see evidence screenshots under `docs/assets/dynamodb/`

---

## SQS Messaging Baseline

Creates the initial SQS messaging baseline for the platform.

Implemented via:

- `modules/sqs`

This environment currently wires in:

- one standard queue: `notification-dispatch`
- one dedicated dead-letter queue for that source queue

Why this module is wired now:

- the platform already reserves SQS for asynchronous work after durable state changes
- notification dispatch is the clearest first async side effect to separate from API response time
- the queue and DLQ establish a concrete messaging extension point without changing the synchronous RSVP write path

Important design notes:

- the queue is intended for durable post-commit notification work
- notification delivery behavior and consumers are not implemented yet
- the primary RSVP business write remains synchronous through DynamoDB durable commit
- IAM permissions for queue producers and consumers are deferred to the workload IAM step

The environment should stay thin:

- reusable AWS resource logic belongs in modules
- `envs/dev` should focus on composition and environment-level identity and placement inputs

Validation:

- validated via `terraform apply -target="module.sqs"`, AWS inspection, and a clean post-apply `terraform plan`
- confirmed source queue creation, DLQ creation, redrive configuration, and queue attribute values
- confirmed Terraform outputs match the created queue and DLQ identities
- see evidence screenshots under `docs/assets/sqs/`

---

## IAM Roles (Lambda Execution Baseline)

Creates the initial Lambda execution IAM baseline for the platform.

Implemented via:

- `modules/iam`

This environment currently wires in:

- one execution role for `create-event`
- one execution role for `get-event`
- one execution role for `list-events`
- one execution role for `update-event`
- one execution role for `cancel-event`
- one execution role for `rsvp`
- one execution role for `get-event-rsvps`
- one execution role for `notification-worker`

Why this module is wired now:

- the Lambda compute layer comes next in the rollout order
- workload execution roles should exist before functions are introduced
- the platform now has enough real DynamoDB and SQS resources to bind least-privilege IAM to concrete ARNs

Important design notes:

- each workload gets its own least-privilege execution role and customer-managed policy
- `get-event` intentionally stays narrower than `list-events` and receives only direct `GetItem` access for the events table
- `update-event` receives narrow `GetItem` + `UpdateItem` access for the events table
- `cancel-event` receives narrow `GetItem` + `UpdateItem` access for the events table
- `rsvp` is the special transactional role spanning both DynamoDB business tables
- `get-event-rsvps` is the read-only RSVP visibility role and receives:
  - `GetItem` on the `events` table
  - `Query` on the `rsvps` table
- `rsvp` intentionally has no SQS permissions
- only `notification-worker` gets SQS consumer permissions
- `list-events` currently includes temporary `Scan` access only as a short-term contract accommodation

The environment should stay thin:

- reusable AWS resource logic belongs in modules
- `envs/dev` should focus on composition and environment-level identity and placement inputs

Validation:

- validated via `terraform apply`, AWS inspection, and a clean post-apply `terraform plan`
- confirmed all wired workload roles were created with Lambda-only trust relationships
- confirmed `get-event` has narrow direct-read access for the events table
- confirmed `update-event` has narrow read/write access for the events table
- confirmed `cancel-event` has narrow read/write access for the events table
- confirmed the RSVP policy includes transactional DynamoDB access across both business tables
- confirmed `get-event-rsvps` has read-only DynamoDB access across the two business tables:
  - `GetItem` on `events`
  - `Query` on `rsvps`
- confirmed only `notification-worker` has SQS consumer permissions
- confirmed Terraform outputs match the created IAM role identities
- see evidence screenshots under `docs/assets/iam/`

---

## Lambda Compute Baseline

Creates the first real Lambda compute baseline for the platform.

Implemented via:

- `modules/lambda`

### Lambda workloads

This environment currently wires in these deployed Lambda workloads:

- `create-event`
- `get-event`
- `list-events`
- `update-event`
- `cancel-event`
- `rsvp`
- `get-event-rsvps`

Why this module is wired now:

- the platform now has the minimum supporting layers needed for real compute:
  - DynamoDB business tables
  - workload IAM roles
- the platform can validate both synchronous write paths and multiple read paths end to end in AWS
- packaging stays outside Terraform, while deployment stays inside the reusable Lambda module

Important design notes:

- the Lambda module remains infrastructure-focused and consumes a prepared ZIP artifact
- `envs/dev` stays thin and composition-only
- each deployed function uses its matching least-privilege IAM role
- each deployed function receives only the environment variables it actually needs:
  - all current Lambda workloads receive `EVENTS_TABLE_NAME`
  - `rsvp` and `get-event-rsvps` also receive `RSVPS_TABLE_NAME`
- all deployed functions return an API Gateway-style wrapped response even before API Gateway is wired
- reusable AWS resource logic belongs in modules
- packaging is prepared before Terraform

Current business behavior validated in this environment:

- `create-event`
  - authenticated event creation succeeds
  - non-admin admin-only creation is rejected
  - canonical event items are written with `status = ACTIVE`
  - request-body `creator_id` spoofing is ignored in favor of caller-context ownership
  - public events populate the public upcoming GSI, while non-public events omit those helper attributes
- `list-events`
  - `mode=all` succeeds
  - `mode=mine` succeeds with caller context
  - `mode=mine` without caller context returns `400`
  - returned items use the locked public event DTO and hide internal storage helper fields
  - `mode=all` excludes cancelled events during the current scan-based phase
  - `mode=mine` still includes cancelled owner events
- `get-event`
  - successful single-item lookup returns `200`
  - missing event returns `404`
  - single-item reads do not require caller context
  - returned items use the locked public event DTO under `item`
  - direct DynamoDB `GetItem` lookup is used by canonical `event_pk`
- `update-event`
  - creator-owned and admin updates succeed
  - unauthorized updates return `403`
  - invalid update input returns `400`
  - capacity reductions below current `attending_count` return `400`
  - cancelled events cannot be updated
  - direct invocation and API Gateway-style body input both work
  - partial updates preserve omitted mutable fields
  - returned updated items use the locked public event DTO under `item`
- `cancel-event`
  - creator-owned cancel succeeds
  - unauthorized cancel returns `403`
  - repeated cancel returns `200`
  - cancelled items use the locked public event DTO under `item`
  - `status = CANCELLED` is returned
  - public GSI helper attributes are removed while creator visibility helpers remain in storage
- `rsvp`
  - public events allow anonymous and authenticated RSVP
  - protected events require authentication
  - admin-only events require an authenticated admin caller
  - successful anonymous RSVP to a public event returns `201`
  - same-subject overwrite returns `200` with `operation = "updated"`
  - protected-event anonymous RSVP returns `403`
  - admin-only RSVP by a non-admin caller returns `403`
  - full-capacity attending RSVP returns `400`
  - full-capacity not-attending RSVP still succeeds
  - cancelled events reject RSVP with `400`
  - RSVP writes remain synchronous and transactional across the `events` and `rsvps` tables
  - responses expose the locked public RSVP contract:
    - `item`
    - `event_summary`
    - `operation`
- `get-event-rsvps`
  - creator-owned RSVP reads return `200`
  - admin RSVP reads return `200`
  - anonymous and non-owner non-admin callers are rejected with `403`
  - missing events return `404`
  - request resolution supports:
    - direct invocation input
    - API Gateway-style `pathParameters` and `queryStringParameters`
  - response body uses the locked public RSVP read contract:
    - `event`
    - `items`
    - `stats`
    - `next_cursor`
  - internal storage fields stay hidden from the response
  - cancelled and past events remain readable for the creator and admins
  - pagination works through opaque `next_cursor`

Public event DTO behavior validated across the event read/update/cancel flows:

- returned event items use the locked public DTO contract:
  - `event_id`
  - `status`
  - `title`
  - `date`
  - `description`
  - `location`
  - `capacity`
  - `is_public`
  - `requires_admin`
  - `created_by`
  - `created_at`
  - `rsvp_count`
  - `attending_count`
- internal GSI helper fields and `not_attending_count` stay hidden from the public event response shape
- `capacity = null` is preserved for unlimited-capacity events
- frontend is expected to render user-friendly timestamp formatting from backend-provided ISO UTC timestamps

Validation:

- validated via external artifact packaging, `terraform apply`, Lambda invocation, DynamoDB inspection, CloudWatch logs inspection, and a clean post-apply `terraform plan`
- confirmed deployed function names and log groups for:
  - `create-event`
  - `get-event`
  - `list-events`
  - `update-event`
  - `cancel-event`
  - `rsvp`
  - `get-event-rsvps`
- confirmed Terraform outputs match the created Lambda and log group identities
- see evidence screenshots under `docs/assets/lambda/`

---

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
| ---- | ------- |
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | ~> 1.14.0 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | ~> 6.37 |



## Modules

| Name | Source | Version |
| ---- | ------ | ------- |
| <a name="module_dynamodb_data_layer"></a> [dynamodb\_data\_layer](#module\_dynamodb\_data\_layer) | ../../modules/dynamodb_data_layer | n/a |
| <a name="module_iam"></a> [iam](#module\_iam) | ../../modules/iam | n/a |
| <a name="module_lambda"></a> [lambda](#module\_lambda) | ../../modules/lambda | n/a |
| <a name="module_sqs"></a> [sqs](#module\_sqs) | ../../modules/sqs | n/a |



## Inputs

| Name | Description | Type | Default | Required |
| ---- | ----------- | ---- | ------- | :------: |
| <a name="input_aws_region"></a> [aws\_region](#input\_aws\_region) | AWS region where resources will be deployed. | `string` | n/a | yes |
| <a name="input_environment"></a> [environment](#input\_environment) | Deployment environment name. | `string` | n/a | yes |
| <a name="input_project_name"></a> [project\_name](#input\_project\_name) | Project name used for naming and tagging resources. | `string` | n/a | yes |
| <a name="input_dynamodb_point_in_time_recovery_enabled"></a> [dynamodb\_point\_in\_time\_recovery\_enabled](#input\_dynamodb\_point\_in\_time\_recovery\_enabled) | Enable point-in-time recovery for DynamoDB tables in this environment. | `bool` | `false` | no |

## Outputs

| Name | Description |
| ---- | ----------- |
| <a name="output_events_table_arn"></a> [events\_table\_arn](#output\_events\_table\_arn) | ARN of the DynamoDB events table created for the dev environment. |
| <a name="output_events_table_name"></a> [events\_table\_name](#output\_events\_table\_name) | Name of the DynamoDB events table created for the dev environment. |
| <a name="output_iam_role_arns"></a> [iam\_role\_arns](#output\_iam\_role\_arns) | Map of workload IAM role ARNs for the dev environment. |
| <a name="output_iam_role_names"></a> [iam\_role\_names](#output\_iam\_role\_names) | Map of workload IAM role names for the dev environment. |
| <a name="output_lambda_function_arns"></a> [lambda\_function\_arns](#output\_lambda\_function\_arns) | Map of workload Lambda function ARNs for the dev environment. |
| <a name="output_lambda_function_names"></a> [lambda\_function\_names](#output\_lambda\_function\_names) | Map of workload Lambda function names for the dev environment. |
| <a name="output_lambda_invoke_arns"></a> [lambda\_invoke\_arns](#output\_lambda\_invoke\_arns) | Map of workload Lambda invoke ARNs for the dev environment. |
| <a name="output_lambda_log_group_arns"></a> [lambda\_log\_group\_arns](#output\_lambda\_log\_group\_arns) | Map of workload CloudWatch Logs log group ARNs for the dev environment. |
| <a name="output_lambda_log_group_names"></a> [lambda\_log\_group\_names](#output\_lambda\_log\_group\_names) | Map of workload CloudWatch Logs log group names for the dev environment. |
| <a name="output_rsvps_table_arn"></a> [rsvps\_table\_arn](#output\_rsvps\_table\_arn) | ARN of the DynamoDB RSVP table created for the dev environment. |
| <a name="output_rsvps_table_name"></a> [rsvps\_table\_name](#output\_rsvps\_table\_name) | Name of the DynamoDB RSVP table created for the dev environment. |
| <a name="output_sqs_dlq_arns"></a> [sqs\_dlq\_arns](#output\_sqs\_dlq\_arns) | Map of logical queue key to rendered SQS DLQ ARN for queues that create a dedicated DLQ in the dev environment. |
| <a name="output_sqs_dlq_names"></a> [sqs\_dlq\_names](#output\_sqs\_dlq\_names) | Map of logical queue key to rendered SQS DLQ name for queues that create a dedicated DLQ in the dev environment. |
| <a name="output_sqs_dlq_urls"></a> [sqs\_dlq\_urls](#output\_sqs\_dlq\_urls) | Map of logical queue key to rendered SQS DLQ URL for queues that create a dedicated DLQ in the dev environment. |
| <a name="output_sqs_queue_arns"></a> [sqs\_queue\_arns](#output\_sqs\_queue\_arns) | Map of logical queue key to rendered SQS queue ARN for the dev environment. |
| <a name="output_sqs_queue_names"></a> [sqs\_queue\_names](#output\_sqs\_queue\_names) | Map of logical queue key to rendered SQS queue name for the dev environment. |
| <a name="output_sqs_queue_urls"></a> [sqs\_queue\_urls](#output\_sqs\_queue\_urls) | Map of logical queue key to rendered SQS queue URL for the dev environment. |
<!-- END_TF_DOCS -->
