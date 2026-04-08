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
- confirmed only `notification-worker` has SQS consumer permissions
- confirmed Terraform outputs match the created IAM role identities
- see evidence screenshots under `docs/assets/iam/`

---

## Lambda Compute Baseline

Creates the first real Lambda compute baseline for the platform.

Implemented via:

- `modules/lambda`

### Lambda workloads

This environment currently wires in:

- deployed Lambda workloads:
  - `create-event`
  - `get-event`
  - `list-events`
  - `update-event`
  - `cancel-event`
  - `rsvp`

Why this module is wired now:

- the platform now has the minimum supporting layers needed for real compute:
  - DynamoDB business tables
  - workload IAM roles
- the platform can now validate the first real business write path and multiple
  real business read paths end to end in AWS
- packaging stays outside Terraform, while deployment stays inside the reusable Lambda module

Important design notes:

- the Lambda module remains infrastructure-focused and consumes a prepared ZIP artifact
- `envs/dev` stays thin and composition-only
- the deployed `create-event` function uses the existing least-privilege IAM `create-event` role
- the deployed `get-event` function uses the existing least-privilege IAM `get-event` role
- the deployed `list-events` function uses the existing least-privilege IAM `list-events` role
- the deployed `update-event` function uses the existing least-privilege IAM `update-event` role
- the deployed `cancel-event` function uses the existing least-privilege IAM `cancel-event` role
- the deployed `rsvp` function uses the existing least-privilege IAM `rsvp` role
- each deployed function receives only the environment variables it actually needs:
  - `EVENTS_TABLE_NAME`
  - `rsvp` also receives `RSVPS_TABLE_NAME`
- all deployed functions return an API Gateway-style wrapped response even before API Gateway is wired
- event creation is authenticated-only in the current platform contract
- event ownership is derived from caller context rather than a request-body `creator_id`
- admin-only events require admin caller context
- single-item event reads are intentionally public in the current platform contract
- broad event listing remains intentionally available through `mode=all`
- creator-scoped event listing uses `mode=mine` with caller identity from `requestContext.authorizer.user_id`
- RSVP authorization depends on event type:
  - public events allow anonymous and authenticated RSVP
  - protected events require authentication
  - admin-only events require an authenticated admin caller
- RSVP writes remain synchronous and transactional across the `events` and `rsvps` tables
- RSVP responses expose the public RSVP contract:
  - `item`
  - `event_summary`
  - `operation`

Current business behavior validated in this step:

- direct successful creation of a public event by an authenticated caller
- direct successful creation of a protected event by an authenticated caller
- direct successful creation of an admin-only event by an admin caller
- canonical event item write into the `events` table
- new canonical event records include `status = ACTIVE`
- request-body `creator_id` spoofing is ignored in favor of caller-context ownership
- non-admin callers are rejected when attempting to create admin-only events
- sparse public GSI behavior:
  - public events are written to the public upcoming index
  - non-public events omit the public index attributes
- direct successful broad event listing through `mode=all`
- direct successful creator-scoped event listing through `mode=mine`
- `mine` mode without caller context returns `400`
- direct successful single-item event read through `event_id`
- missing single-item event read returns `404`
- single-item event read does not require caller context
- direct successful partial event update by the event creator
- direct successful partial event update by an admin caller
- unauthorized partial event update returns `403`
- invalid partial update input returns `400`
- capacity reductions below current `attending_count` return `400`
- direct successful event cancellation by the event creator
- unauthorized cancel attempt returns `403`
- repeated cancel returns `200` idempotently
- cancelling an event sets `status = CANCELLED`
- cancelling an event removes public discovery helper attributes while preserving creator visibility helpers
- direct successful anonymous RSVP to a public event returns `201`
- same-subject RSVP overwrite returns `200` with `operation = "updated"`
- anonymous RSVP to a protected event returns `403`
- authenticated RSVP to a protected event succeeds
- non-admin RSVP to an admin-only event returns `403`
- full-capacity attending RSVP returns `400`
- not-attending RSVP is still allowed for a full event
- cancelled events reject RSVP with `400`
- partial updates preserve omitted mutable fields (no implicit overwrites)
- API Gateway-style body input is supported for `update-event`
- `body` takes precedence over top-level mutable fields for `update-event`
- `pathParameters.event_id` takes precedence over top-level `event_id` for `update-event`
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
- internal GSI helper fields and `not_attending_count` stay hidden from the response shape
- `capacity = null` is preserved for unlimited-capacity events
- frontend is expected to render user-friendly timestamp formatting from backend-provided ISO UTC timestamps
- `get-event` uses direct DynamoDB `GetItem` lookup by canonical `event_pk`

The environment should stay thin:

- reusable AWS resource logic belongs in modules
- packaging is prepared before Terraform
- `envs/dev` should focus on composition and environment-level identity and placement inputs

Validation:

- validated via external artifact packaging, `terraform apply`, Lambda invocation, DynamoDB inspection, CloudWatch logs inspection, and a clean post-apply `terraform plan`
- confirmed the deployed function name is `aws-serverless-events-platform-dev-create-event`
- confirmed the log group is `/aws/lambda/aws-serverless-events-platform-dev-create-event`
- confirmed successful authenticated invocation returns `201` with the wrapped response body
- confirmed the returned create-event `item` uses the locked public event DTO
- confirmed returned created items include `status = ACTIVE`
- confirmed missing caller context returns `400`
- confirmed non-admin admin-only creation returns `400`
- confirmed the Lambda writes the expected canonical event item shape into DynamoDB
- confirmed stored created event items include `status = ACTIVE`
- confirmed `creator_id` is derived from caller context
- confirmed non-public events omit the public GSI attributes
- confirmed the deployed function name is `aws-serverless-events-platform-dev-get-event`
- confirmed the log group is `/aws/lambda/aws-serverless-events-platform-dev-get-event`
- confirmed successful single-item invocation returns `200`
- confirmed missing item invocation returns `404`
- confirmed single-item reads do not require caller context
- confirmed returned items use the locked public event DTO under `item`
- confirmed the deployed function name is `aws-serverless-events-platform-dev-list-events`
- confirmed the log group is `/aws/lambda/aws-serverless-events-platform-dev-list-events`
- confirmed successful `mode=all` invocation returns `200`
- confirmed successful `mode=mine` invocation returns `200`
- confirmed `mode=mine` without caller context returns `400`
- confirmed returned items use the locked public event DTO and hide internal storage helper fields
- confirmed `mode=all` excludes cancelled events during the current scan-based phase
- confirmed `mode=mine` still includes cancelled owner events
- confirmed the deployed function name is `aws-serverless-events-platform-dev-update-event`
- confirmed the log group is `/aws/lambda/aws-serverless-events-platform-dev-update-event`
- confirmed successful creator-owned partial update returns `200`
- confirmed unauthorized partial update returns `403`
- confirmed invalid capacity reduction returns `400`
- confirmed `status` is rejected as immutable update input with `400`
- confirmed cancelled events cannot be updated and return `400`
- confirmed conditional write protection (DynamoDB `ConditionExpression`) prevents capacity race conditions
- confirmed direct invocation and API Gateway-style body input both work for `update-event`
- confirmed returned updated items use the locked public event DTO under `item`
- confirmed internal storage helper fields remain hidden from updated responses
- confirmed the deployed function name is `aws-serverless-events-platform-dev-cancel-event`
- confirmed the log group is `/aws/lambda/aws-serverless-events-platform-dev-cancel-event`
- confirmed successful creator-owned cancel returns `200`
- confirmed unauthorized cancel returns `403`
- confirmed repeated cancel returns `200`
- confirmed returned cancelled items use the locked public event DTO under `item`
- confirmed returned cancelled items include `status = CANCELLED`
- confirmed cancel removes public GSI helper attributes while preserving creator visibility helpers in storage
- confirmed the deployed function name is `aws-serverless-events-platform-dev-rsvp`
- confirmed the log group is `/aws/lambda/aws-serverless-events-platform-dev-rsvp`
- confirmed successful anonymous RSVP to a public event returns `201`
- confirmed same-subject overwrite returns `200` with `operation = "updated"`
- confirmed protected-event anonymous RSVP returns `403`
- confirmed admin-only RSVP by a non-admin caller returns `403`
- confirmed full-capacity attending RSVP returns `400`
- confirmed full-capacity not-attending RSVP still succeeds
- confirmed cancelled events reject RSVP with `400`
- confirmed RSVP writes the expected canonical item shape into the `rsvps` table
- confirmed RSVP updates helper counters on the canonical event item in DynamoDB
- confirmed RSVP responses hide internal storage fields and expose the locked public RSVP contract
- confirmed Terraform outputs match the created Lambda and log group identities
- see evidence screenshots under `docs/assets/lambda/`

---

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | ~> 1.14.0 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | ~> 6.37 |

## Providers

No providers.

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_dynamodb_data_layer"></a> [dynamodb\_data\_layer](#module\_dynamodb\_data\_layer) | ../../modules/dynamodb_data_layer | n/a |
| <a name="module_iam"></a> [iam](#module\_iam) | ../../modules/iam | n/a |
| <a name="module_lambda"></a> [lambda](#module\_lambda) | ../../modules/lambda | n/a |
| <a name="module_sqs"></a> [sqs](#module\_sqs) | ../../modules/sqs | n/a |

## Resources

No resources.

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_aws_region"></a> [aws\_region](#input\_aws\_region) | AWS region where resources will be deployed. | `string` | n/a | yes |
| <a name="input_dynamodb_point_in_time_recovery_enabled"></a> [dynamodb\_point\_in\_time\_recovery\_enabled](#input\_dynamodb\_point\_in\_time\_recovery\_enabled) | Enable point-in-time recovery for DynamoDB tables in this environment. | `bool` | `false` | no |
| <a name="input_environment"></a> [environment](#input\_environment) | Deployment environment name. | `string` | n/a | yes |
| <a name="input_project_name"></a> [project\_name](#input\_project\_name) | Project name used for naming and tagging resources. | `string` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
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
