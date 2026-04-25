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

Defines the Lambda execution IAM baseline for the platform.

Implemented via:

- `modules/iam`

This environment currently wires in:

- one execution role for `create-event`
- one execution role for `get-event`
- one execution role for `list-events`
- one execution role for `list-my-events`
- one execution role for `update-event`
- one execution role for `cancel-event`
- one execution role for `rsvp-authorizer`
- one execution role for `rsvp`
- one execution role for `get-event-rsvps`
- one execution role for `notification-worker`

Why this module is wired now:

- workload execution roles must exist before Lambda functions can be deployed cleanly
- the platform now has real DynamoDB and SQS resources available for least-privilege IAM binding
- the environment can now validate workload-specific execution roles against concrete AWS resource ARNs

Important design notes:

- each workload gets its own least-privilege execution role and customer-managed policy
- `create-event` receives write access for creating canonical event records in the `events` table
- `get-event` receives only direct `GetItem` access for the `events` table
- `list-events` currently receives temporary `Scan` access for the `events` table as a short-term access-pattern accommodation
- `list-my-events` receives `Query` access for the `creator-events` GSI
- `update-event` and `cancel-event` receive narrow `GetItem` + `UpdateItem` access for the `events` table
- `rsvp` is the transactional workload role and spans both business tables so it can:
  - read the current event state
  - read the current RSVP state
  - perform the transactional write across `events` and `rsvps`
- `get-event-rsvps` is the read-only RSVP visibility role and receives:
  - `GetItem` on `events`
  - `Query` on `rsvps`
- `rsvp-authorizer` uses a logs-only execution profile because Cognito token validation and JWKS retrieval happen without direct Cognito IAM access
- `notification-worker` is the only workload that currently receives SQS consumer permissions

The environment should stay thin:

- reusable AWS resource logic belongs in modules
- `envs/dev` should focus on composition and environment-level identity and placement inputs

Validation:

- validated via `terraform apply`, AWS inspection, and a clean post-apply `terraform plan`
- confirmed all wired workload roles were created with Lambda-only trust relationships
- confirmed `get-event` has narrow direct-read access for the events table
- confirmed `list-events` has temporary `Scan` access for the events table only
- confirmed `list-my-events` has narrow `Query` access for the `creator-events` GSI
- confirmed `update-event` has narrow read/write access for the events table
- confirmed `cancel-event` has narrow read/write access for the events table
- confirmed `rsvp-authorizer` has the logs-only execution profile and no DynamoDB or SQS permissions
- confirmed the RSVP policy includes transactional DynamoDB access across both business tables
- confirmed `get-event-rsvps` has read-only DynamoDB access across the two business tables:
  - `GetItem` on `events`
  - `Query` on `rsvps`
- confirmed only `notification-worker` has SQS consumer permissions
- confirmed Terraform outputs match the created IAM role identities
- see evidence screenshots under `docs/assets/iam/`

---

## Cognito Identity Baseline

Creates the initial managed identity baseline for the platform.

Implemented via:

- `modules/cognito`

This environment currently wires in:

- one Cognito User Pool
- one public Cognito User Pool Client
- one Cognito User Group: `admin`

Why this module is wired now:

- the platform has already locked Cognito as the managed identity provider
- `envs/dev` now needs a real identity baseline before routed authenticated API behavior can be introduced

Important design notes:

- Cognito owns identity lifecycle
- the routed API uses a hybrid auth model:
  - native JWT authorization for ordinary protected routes
  - a dedicated custom Lambda authorizer for the mixed-mode `rsvp` route
- business Lambda handlers remain free of generic authentication logic
- business Lambda handlers consume normalized caller context rather than depending directly on a single raw authorizer shape
- the canonical identity baseline remains:
  - Cognito `sub` for user identity
  - Cognito `admin` group membership for admin capability
- the current baseline intentionally stays small:
  - username is the primary sign-in attribute in v1
  - email is required
  - email verification is Cognito-managed
  - self sign-up is enabled
  - MFA is disabled in this phase
  - hosted UI, social login, triggers, scopes, domains, and user seeding are not part of this step
- `envs/dev` explicitly sets Cognito deletion protection to disabled for this non-production environment

The environment should stay thin:

- reusable AWS resource logic belongs in modules
- `envs/dev` should focus on composition and environment-level identity and placement inputs

Validation:

- validated via `terraform apply`, AWS Console inspection, Terraform output verification, and a clean post-apply `terraform plan`
- confirmed the Cognito User Pool was created in `eu-central-1`
- confirmed the rendered User Pool name is `aws-serverless-events-platform-dev-users`
- confirmed the rendered public app client name is `aws-serverless-events-platform-dev-app-client`
- confirmed the `admin` Cognito group was created
- confirmed the app client is public and has no client secret
- confirmed the app client enables:
  - username/password auth
  - refresh token auth
  - SRP auth
- confirmed token revocation and prevent-user-existence hardening are enabled
- confirmed Terraform outputs match the created User Pool, app client, issuer, and admin group identities
- see evidence screenshots under `docs/assets/cognito/`

---

## API Gateway Routed API Baseline

This is the current end-to-end validated routed backend baseline in the platform:
Cognito → API Gateway → Lambda → DynamoDB.

This section documents the routed API baseline currently deployed in `envs/dev`.

Implemented via:

- `modules/api_gateway`

This environment currently wires in:

- one HTTP API
- one stage
- one environment-owned CloudWatch Logs log group for API Gateway stage access logs
- one JWT authorizer (Cognito-based)
- one Lambda request authorizer for the mixed-mode RSVP route
- stage access logging for the HTTP API
- default stage throttling
- eight routed API endpoints:
  - `POST /events`
  - `PATCH /events/{event_id}`
  - `POST /events/{event_id}/cancel`
  - `POST /events/{event_id}/rsvp`
  - `GET /events/{event_id}/rsvps`
  - `GET /events`
  - `GET /events/mine`
  - `GET /events/{event_id}`
- eight Lambda integrations:
  - `create-event`
  - `update-event`
  - `cancel-event`
  - `rsvp`
  - `get-event-rsvps`
  - `list-events`
  - `list-my-events`
  - `get-event`

Why this module is wired now:

- the platform needed to validate public and JWT-protected Lambda handlers end to end through API Gateway
- the routed API rollout was implemented incrementally, adding and validating one path per Lambda
- currently implemented and validated routes are:
  - `POST /events`
  - `PATCH /events/{event_id}`
  - `POST /events/{event_id}/cancel`
  - `POST /events/{event_id}/rsvp`
  - `GET /events/{event_id}/rsvps`
  - `GET /events`
  - `GET /events/mine`
  - `GET /events/{event_id}`

Important design notes:

- this remains the routed backend baseline behind the CloudFront edge layer
- the stage-qualified API Gateway invoke URL remains useful for direct backend
  testing and diagnostics, but it is not the intended browser-facing product
  entry point
- CloudFront preserves the existing routed backend path contract instead of
  introducing a separate translated browser-facing API path family
- API Gateway stage access logs are now enabled in `dev`
- the API Gateway access-log log group is owned by `envs/dev`, while the reusable module owns the stage logging configuration
- stage throttling is configured in `dev` as a backend protection baseline
  behind CloudFront
- stricter per-route throttling is now applied to the more write-sensitive routes:
  - `POST /events`
  - `PATCH /events/{event_id}`
  - `POST /events/{event_id}/cancel`
  - `POST /events/{event_id}/rsvp`
- CORS remains intentionally disabled in `dev` because normal browser traffic
  is expected to enter through the same-origin CloudFront path
- `GET /events` is intentionally a public route with `authorization_type = NONE`
- ordinary protected routes use native JWT authorization at API Gateway
- `GET /events/mine` is intentionally JWT-protected so API Gateway enforces the creator-route authentication boundary
- the mixed-mode RSVP authorizer is now implemented as a Lambda request authorizer
- the real mixed-mode `rsvp` business route is now validated through API Gateway using that authorizer
- the business `create-event`, `list-my-events`, `update-event`, `cancel-event`, and `get-event-rsvps` Lambdas consume normalized caller context instead of parsing JWTs directly
- the business `rsvp` Lambda now also consumes normalized caller context instead of parsing raw authorizer payloads directly
- reusable API Gateway logic belongs in modules while `envs/dev` stays composition-oriented

Validation:

- validated via `terraform apply`, AWS Console inspection, Terraform output verification, real Cognito token acquisition, routed API invocation, Lambda execution verification, and a clean post-apply `terraform plan`
- confirmed the HTTP API was created in `eu-central-1`
- confirmed the rendered API name is `aws-serverless-events-platform-dev-http-api`
- confirmed the stage name is `dev`
- confirmed the API Gateway stage access-log log group is owned by the environment and separate from Lambda log groups
- confirmed stage access logging is configured on the deployed API Gateway stage
- confirmed the deployed stage access-log destination is:
  - `/aws/apigateway/aws-serverless-events-platform-dev-http-api-access`
- confirmed default stage throttling is configured on the deployed API Gateway stage
- confirmed stricter per-route throttling overrides are configured for:
  - `POST /events`
  - `PATCH /events/{event_id}`
  - `POST /events/{event_id}/cancel`
  - `POST /events/{event_id}/rsvp`
- confirmed CORS remains disabled in `dev`
- confirmed the mixed-mode request authorizer remains configured with:
  - payload format version `2.0`
  - simple responses enabled
  - TTL `0`
  - identity sources omitted
- confirmed the route keys are:
  - `POST /events`
  - `PATCH /events/{event_id}`
  - `POST /events/{event_id}/cancel`
  - `POST /events/{event_id}/rsvp`
  - `GET /events/{event_id}/rsvps`
  - `GET /events`
  - `GET /events/mine`
  - `GET /events/{event_id}`
- confirmed JWT authorization is attached to the protected routes
- confirmed anonymous requests are rejected at the API edge for JWT-protected routes
- confirmed authenticated `create-event` invocation succeeds through API Gateway with JWT validation
- confirmed admin-only creation behavior is enforced correctly by the Lambda through the routed path
- confirmed event items are successfully written to DynamoDB through the routed path
- confirmed authenticated owner `update-event` invocation succeeds through API Gateway with JWT validation
- confirmed authenticated admin `update-event` invocation succeeds through API Gateway with JWT validation
- confirmed authenticated non-owner `update-event` invocation returns `403`
- confirmed cancelled-event `update-event` invocation returns `400`
- confirmed immutable-field and malformed-body validation still work through the routed `update-event` path
- confirmed event updates are successfully applied through the routed path
- confirmed authenticated owner `cancel-event` invocation succeeds through API Gateway with JWT validation
- confirmed authenticated admin `cancel-event` invocation succeeds through API Gateway with JWT validation
- confirmed authenticated non-owner `cancel-event` invocation returns `403`
- confirmed repeated routed `cancel-event` invocation remains idempotent and returns `200`
- confirmed successful routed cancel removes public discovery helpers while keeping creator visibility helpers in storage
- confirmed event cancellation is successfully applied through the routed path
- confirmed authenticated creator `get-event-rsvps` invocation succeeds through API Gateway with JWT validation
- confirmed authenticated admin `get-event-rsvps` invocation succeeds through API Gateway with JWT validation
- confirmed authenticated non-owner `get-event-rsvps` invocation returns `403`
- confirmed missing-event routed `get-event-rsvps` invocation returns `404`
- confirmed empty-RSVP routed `get-event-rsvps` invocation returns `200` with an empty `items` array
- confirmed RSVP-read results are successfully returned through the routed path
- confirmed routed `get-event-rsvps` responses expose the locked RSVP-read contract:
  - `event`
  - `items`
  - `stats`
  - `next_cursor`
- confirmed `GET /events` is public and has no attached authorizer
- confirmed unauthenticated `GET /events` succeeds through API Gateway with `200`
- confirmed routed public `GET /events` responses filter cancelled events during the current temporary scan-based phase
- confirmed due to the temporary scan-based access path, routed public `GET /events` responses may still include active non-public and past events in the current contract
- confirmed unauthenticated `GET /events/mine` is rejected at the API edge with `401`
- confirmed authenticated creator `GET /events/mine` succeeds through API Gateway with JWT validation
- confirmed authenticated admin `GET /events/mine` succeeds through API Gateway with JWT validation and returns only the admin caller's own events
- confirmed API Gateway access-log entries are written to the dedicated API Gateway access-log group for:
  - `GET /events`
  - `GET /events/mine`
  - `POST /events/{event_id}/rsvp`
- confirmed `GET /events/{event_id}` is public and has no attached authorizer
- confirmed unauthenticated `GET /events/{event_id}` succeeds through API Gateway with `200`
- confirmed routed `GET /events/{event_id}` still returns cancelled events by ID
- confirmed routed `GET /events/{event_id}` still returns non-public events by ID
- confirmed missing-event routed `get-event` invocation returns `404`
- confirmed routed `GET /events/mine` responses include creator-owned cancelled events
- confirmed routed `GET /events/mine` pagination works through:
  - `limit`
  - opaque `next_cursor`
- confirmed normalized caller context is correctly resolved inside business Lambdas from JWT authorizer input
- confirmed the mixed-mode RSVP authorizer is attached to routed `POST /events/{event_id}/rsvp`
- confirmed anonymous public `POST /events/{event_id}/rsvp` succeeds through API Gateway with `201`
- confirmed authenticated user `POST /events/{event_id}/rsvp` succeeds through API Gateway where allowed
- confirmed authenticated admin `POST /events/{event_id}/rsvp` succeeds through API Gateway where allowed
- confirmed an earlier malformed RSVP validation request returned `400` because the request body was not valid JSON, not because of an API Gateway routing or authorizer regression
- confirmed malformed or invalid presented auth for routed `POST /events/{event_id}/rsvp` is denied at the API edge with `403`
- confirmed anonymous routed `POST /events/{event_id}/rsvp` to a protected event returns `403`
- confirmed non-admin routed `POST /events/{event_id}/rsvp` to an admin-only event returns `403`
- confirmed full-capacity routed `POST /events/{event_id}/rsvp` with `attending = true` returns `400`
- confirmed full-capacity routed `POST /events/{event_id}/rsvp` with `attending = false` still succeeds
- confirmed cancelled-event routed `POST /events/{event_id}/rsvp` returns `400`
- confirmed past-event routed `POST /events/{event_id}/rsvp` returns `400`
- confirmed normalized caller context is correctly resolved inside the `rsvp` Lambda from the mixed-mode request authorizer input
- confirmed Terraform outputs match the deployed API ID, stage URL, authorizer ID, and route wiring
- see evidence screenshots under `docs/assets/lambda_api/`

---

## Lambda Compute Baseline

Defines the current Lambda compute baseline for the platform.

Implemented via:

- `modules/lambda`

### Lambda workloads

This environment currently wires in these deployed Lambda workloads:

- `create-event`
- `list-events`
- `get-event`
- `update-event`
- `cancel-event`
- `rsvp`
- `get-event-rsvps`
- `list-my-events`
- `rsvp-authorizer`

Why this module is wired now:

- the platform now has the minimum supporting layers needed for real compute:
  - DynamoDB business tables
  - workload IAM roles
- the platform can now validate synchronous write paths and both public and authenticated read paths end to end in AWS
- packaging stays outside Terraform, while deployment stays inside the reusable Lambda module

Important design notes:

- the Lambda module remains infrastructure-focused and consumes a prepared ZIP artifact
- `envs/dev` stays thin and composition-only
- each deployed function uses its matching least-privilege IAM role
- each deployed function receives only the environment variables it actually needs:
  - all current Lambda workloads receive `EVENTS_TABLE_NAME`
  - `rsvp` and `get-event-rsvps` also receive `RSVPS_TABLE_NAME`
- `rsvp-authorizer` receives only the Cognito/JWT verification environment it actually needs:
  - `COGNITO_ISSUER`
  - `COGNITO_APP_CLIENT_ID`
  - `COGNITO_ADMIN_GROUP_NAME`
- all deployed functions return an API Gateway-style wrapped response even before API Gateway is wired
- reusable AWS resource logic belongs in modules
- packaging is prepared before Terraform

Current business behavior validated in this environment:

- `create-event`
  - protected routed invocation via `POST /events` succeeds for authenticated callers
  - anonymous routed invocation is rejected at the API edge
  - non-admin admin-only creation is rejected
  - admin admin-only creation succeeds
  - canonical event items are written with `status = ACTIVE`
  - request-body `creator_id` spoofing is ignored in favor of caller-context ownership
  - public events populate the public upcoming GSI, while non-public events omit those helper attributes
- `list-events`
  - broad public listing succeeds
  - this is a public (unauthenticated) listing workload
  - no caller context is required or consumed
  - returned items use the locked public event DTO and hide internal storage helper fields
  - broad listing excludes cancelled events during the current scan-based phase
  - due to the temporary scan-based access path, active non-public and past events may still appear in the current contract
- `list-my-events`
  - authenticated creator-scoped listing succeeds
  - routed invocation via `GET /events/mine` is JWT-protected at API Gateway
  - anonymous routed invocation is rejected at the API edge
  - returned items use the same locked public event DTO as `list-events` and `get-event`
  - creator-scoped listing includes cancelled and past creator-owned events
  - pagination works through:
    - `limit`
    - opaque `next_cursor`
  - the current read path uses the `creator-events` GSI
- `get-event`
  - public routed invocation via `GET /events/{event_id}` succeeds without authentication
  - successful single-item lookup returns `200`
  - missing event returns `404`
  - single-item reads do not require caller context
  - returned items use the locked public event DTO under `item`
  - direct DynamoDB `GetItem` lookup is used by canonical `event_pk`
  - cancelled events remain readable by ID
  - non-public events remain readable by ID
- `update-event`
  - protected routed invocation via `PATCH /events/{event_id}` succeeds for authenticated owners
  - protected routed invocation via `PATCH /events/{event_id}` succeeds for authenticated admins
  - authenticated non-owner routed invocation returns `403`
  - cancelled-event routed invocation returns `400`
  - invalid update input returns `400`
  - capacity reductions below current `attending_count` return `400`
  - cancelled events cannot be updated
  - direct invocation and API Gateway-style body input both work
  - partial updates preserve omitted mutable fields
  - returned updated items use the locked public event DTO under `item`
- `cancel-event`
  - protected routed invocation via `POST /events/{event_id}/cancel` succeeds for authenticated owners
  - protected routed invocation via `POST /events/{event_id}/cancel` succeeds for authenticated admins
  - authenticated non-owner routed invocation returns `403`
  - repeated routed invocation returns `200` idempotently
  - anonymous routed invocation is rejected at the API edge
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
  - protected routed invocation via `GET /events/{event_id}/rsvps` succeeds for authenticated creators
  - protected routed invocation via `GET /events/{event_id}/rsvps` succeeds for authenticated admins
  - authenticated non-owner routed invocation returns `403`
  - missing-event routed invocation returns `404`
  - empty-RSVP routed invocation returns `200` with `items = []`
  - anonymous routed invocation is rejected at the API edge
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
  - `list-my-events`
  - `update-event`
  - `cancel-event`
  - `rsvp`
  - `get-event-rsvps`
  - `rsvp-authorizer`
- confirmed Terraform outputs match the created Lambda and log group identities
- see evidence screenshots under `docs/assets/lambda/`

---

## S3 Frontend Origin Bucket Baseline

Creates the initial private frontend-origin storage baseline for the platform.

Implemented via:

- `modules/s3_frontend_bucket`

This environment currently wires in:

- one private S3 bucket for frontend asset storage behind CloudFront

Why this module is wired now:

- the platform needed a real frontend-origin bucket before CloudFront and WAF could be added cleanly
- the edge-delivery rollout is intentionally being implemented in small module-first and env-wiring-second slices
- a private S3 origin bucket is the storage dependency for the browser-facing CloudFront edge layer

Important design notes:

- this bucket is an origin bucket, not a public website bucket
- direct public access is intentionally blocked
- S3 website hosting is intentionally not used
- `envs/dev` currently keeps bucket versioning disabled to keep this non-production environment lean
- `envs/dev` currently sets `force_destroy = true` so the bucket stays easy to tear down and recreate during iterative edge rollout work
- one tiny placeholder frontend file can now be uploaded for validation without introducing a real frontend implementation yet
- the CloudFront distribution now uses this bucket as its private frontend origin
- reusable AWS resource logic belongs in modules while `envs/dev` stays composition-oriented

Validation:

- validated via `terraform apply`, Terraform output verification, AWS Console inspection, AWS CLI inspection, placeholder object upload, direct public-access check, and a clean post-apply `terraform plan`
- confirmed the bucket was created in `eu-central-1`
- confirmed the rendered bucket name is:
  - `aws-serverless-events-platform-dev-frontend`
- confirmed Terraform outputs match the created bucket identity:
  - `frontend_bucket_arn`
  - `frontend_bucket_id`
  - `frontend_bucket_name`
  - `frontend_bucket_regional_domain_name`
- confirmed bucket-level public access blocking is fully enabled
- confirmed ownership controls use:
  - `BucketOwnerEnforced`
- confirmed default server-side encryption uses:
  - `AES256`
- confirmed bucket versioning is not enabled in `dev`:
  - `Status = Suspended`
- confirmed placeholder `index.html` upload succeeds
- confirmed direct public object access returns:
  - `403 AccessDenied`
- see evidence screenshots under `docs/assets/s3_frontend_bucket/`

---

## WAF Edge Protection Baseline

Creates the initial CloudFront-scoped WAF protection baseline for the platform.

Implemented via:

- `modules/waf`

This environment currently wires in:

- one CloudFront-scoped WAFv2 Web ACL
- a fixed AWS managed-rule baseline
- one simple IP-based rate-limit rule

Why this module is wired now:

- the platform now has private frontend-origin storage and can begin adding the edge protection layer in front of the future CloudFront entry point
- WAF is intentionally introduced before CloudFront wiring so the protection baseline exists before the distribution is attached to it
- the edge-delivery rollout remains split into small module-first and env-wiring-second slices

Important design notes:

- the Web ACL is CloudFront-scoped, so it is managed through the `us-east-1` AWS provider alias
- the Web ACL is now associated with the dev CloudFront distribution through the CloudFront module wiring
- the default Web ACL action is `allow`
- the managed-rule baseline includes:
  - `AWSManagedRulesCommonRuleSet`
  - `AWSManagedRulesKnownBadInputsRuleSet`
  - `AWSManagedRulesAmazonIpReputationList`
- the rate-limit rule blocks requests when one source IP exceeds the configured threshold
- `dev` currently uses a simple rate limit of `2000` requests per five-minute evaluation window
- visibility configuration is enabled for the Web ACL and every rule so metrics and sampled requests are available
- reusable AWS resource logic belongs in modules while `envs/dev` stays composition-oriented

Validation:

- validated via `terraform apply`, Terraform output verification, AWS CLI inspection, AWS Console inspection, tag inspection, and a clean post-apply `terraform plan`
- confirmed the CloudFront-scoped Web ACL was created in `us-east-1`
- confirmed the rendered Web ACL name is:
  - `aws-serverless-events-platform-dev-edge`
- confirmed Terraform outputs match the created Web ACL identity:
  - `waf_web_acl_arn`
  - `waf_web_acl_id`
  - `waf_web_acl_name`
- confirmed the Web ACL scope is:
  - `CLOUDFRONT`
- confirmed the default action is:
  - `allow`
- confirmed the managed-rule baseline is present
- confirmed the rate-limit rule uses:
  - `Limit = 2000`
  - `AggregateKeyType = IP`
  - `Action = Block`
- confirmed Web ACL and rule visibility configuration is enabled
- confirmed expected project, environment, management, and name tags are applied
- confirmed a clean post-apply `terraform plan`
- see evidence screenshots under `docs/assets/waf/`

---

## CloudFront Edge Distribution Baseline

Creates the initial public edge entry-point baseline for the platform.

Implemented via:

- `modules/cloudfront`

This environment currently wires in:

- one CloudFront distribution
- one S3 Origin Access Control for the private frontend origin bucket
- one CloudFront Function for frontend SPA navigation rewrites
- one default static asset behavior backed by the private S3 bucket
- two ordered frontend SPA behaviors for:
  - `/app`
  - `/app/*`
- two ordered API behaviors for:
  - `/events`
  - `/events/*`
- one API Gateway origin using the existing `dev` stage path
- the already-created CloudFront-scoped WAF Web ACL
- one environment-owned S3 bucket policy that allows CloudFront read access to the private frontend bucket

Why this module is wired now:

- the private frontend origin bucket and WAF baseline already exist in `dev`
- the platform now needs CloudFront to become the intended public entry point
- the edge-delivery baseline must prove both static delivery and backend API routing before real frontend implementation starts

Important design notes:

- CloudFront serves `index.html` and future static frontend assets from the private S3 origin bucket
- S3 direct public access remains denied
- CloudFront accesses S3 through Origin Access Control, not legacy Origin Access Identity
- the S3 bucket policy is owned by `envs/dev` because it binds this concrete bucket to this concrete distribution ARN
- API Gateway remains the backend route/auth/integration layer
- CloudFront forwards the existing backend route family through:
  - `/events`
  - `/events/*`
- CloudFront serves frontend application routes under:
  - `/app`
  - `/app/*`
- the `/app` and `/app/*` behaviors use a viewer-request CloudFront Function
  to rewrite eligible browser HTML navigations to `/index.html`
- missing static assets under `/app/*` are not rewritten to the SPA entrypoint
- CloudFront uses the API Gateway domain as the origin and supplies the stage path through `origin_path = /dev`
- WAF is associated with the distribution at the CloudFront edge
- static traffic uses the managed caching-optimized policy
- API traffic uses the managed caching-disabled policy and forwards viewer request details needed by API Gateway
- custom domains, Route 53, ACM certificates, logging buckets, broad custom error response fallbacks, and frontend deployment automation remain out of scope for this environment step
- reusable AWS resource logic belongs in modules while `envs/dev` stays composition-oriented

Validation:

- validated via `terraform apply`, AWS Console inspection, AWS CLI inspection, runtime curl checks, and a clean post-apply `terraform plan`
- confirmed the CloudFront distribution was created and deployed
- confirmed the rendered CloudFront distribution name is:
  - `aws-serverless-events-platform-dev-edge`
- confirmed the CloudFront distribution domain name was created and is exposed via:
  - `cloudfront_distribution_domain_name`
- confirmed Terraform outputs match the created distribution identity:
  - `cloudfront_distribution_id`
  - `cloudfront_distribution_arn`
  - `cloudfront_distribution_domain_name`
  - `cloudfront_distribution_hosted_zone_id`
  - `cloudfront_s3_origin_access_control_id`
  - `cloudfront_spa_rewrite_function_arn`
  - `cloudfront_spa_rewrite_function_name`
- confirmed the distribution has two origins:
  - `s3-frontend-origin`
  - `api-gateway-origin`
- confirmed the S3 origin uses Origin Access Control
- confirmed the API Gateway origin uses the API Gateway domain with origin path:
  - `/dev`
- confirmed behaviors are configured for:
  - default static frontend traffic
  - `/app`
  - `/app/*`
  - `/events`
  - `/events/*`
- confirmed the SPA rewrite CloudFront Function is deployed and attached only to:
  - `/app`
  - `/app/*`
- confirmed WAF is associated with the distribution
- confirmed direct S3 public access to `index.html` returns `403 AccessDenied`
- confirmed CloudFront serves `index.html` successfully
- confirmed CloudFront rewrites eligible `/app` browser HTML navigations to `/index.html`
- confirmed CloudFront rewrites eligible `/app/events/example` browser HTML navigations to `/index.html`
- confirmed missing static assets under `/app/*` return real S3 or CloudFront errors instead of the SPA entrypoint
- confirmed CloudFront routes `/events` to API Gateway successfully
- confirmed CloudFront routes `/events/not-a-real-event` to API Gateway and returns API JSON
- confirmed HTTP requests redirect to HTTPS at CloudFront
- confirmed a clean post-apply `terraform plan`
- see evidence screenshots under `docs/assets/cloudfront/`

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

| Name | Source | Version |
|------|--------|---------|
| <a name="module_api_gateway"></a> [api\_gateway](#module\_api\_gateway) | ../../modules/api_gateway | n/a |
| <a name="module_cloudfront"></a> [cloudfront](#module\_cloudfront) | ../../modules/cloudfront | n/a |
| <a name="module_cognito"></a> [cognito](#module\_cognito) | ../../modules/cognito | n/a |
| <a name="module_dynamodb_data_layer"></a> [dynamodb\_data\_layer](#module\_dynamodb\_data\_layer) | ../../modules/dynamodb_data_layer | n/a |
| <a name="module_iam"></a> [iam](#module\_iam) | ../../modules/iam | n/a |
| <a name="module_lambda"></a> [lambda](#module\_lambda) | ../../modules/lambda | n/a |
| <a name="module_s3_frontend_bucket"></a> [s3\_frontend\_bucket](#module\_s3\_frontend\_bucket) | ../../modules/s3_frontend_bucket | n/a |
| <a name="module_sqs"></a> [sqs](#module\_sqs) | ../../modules/sqs | n/a |
| <a name="module_waf"></a> [waf](#module\_waf) | ../../modules/waf | n/a |

## Resources

| Name | Type |
|------|------|
| [aws_cloudwatch_log_group.api_gateway_access](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_group) | resource |
| [aws_s3_bucket_policy.frontend_origin](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_policy) | resource |
| [aws_iam_policy_document.frontend_bucket_cloudfront_read](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |

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
| <a name="output_api_gateway_api_arn"></a> [api\_gateway\_api\_arn](#output\_api\_gateway\_api\_arn) | ARN of the HTTP API created for the dev environment routed backend baseline. |
| <a name="output_api_gateway_api_endpoint"></a> [api\_gateway\_api\_endpoint](#output\_api\_gateway\_api\_endpoint) | Base invoke endpoint of the HTTP API created for the dev environment routed backend baseline. |
| <a name="output_api_gateway_api_id"></a> [api\_gateway\_api\_id](#output\_api\_gateway\_api\_id) | ID of the HTTP API created for the dev environment routed backend baseline. |
| <a name="output_api_gateway_execution_arn"></a> [api\_gateway\_execution\_arn](#output\_api\_gateway\_execution\_arn) | Execution ARN of the HTTP API created for the dev environment routed backend baseline. |
| <a name="output_api_gateway_jwt_authorizer_id"></a> [api\_gateway\_jwt\_authorizer\_id](#output\_api\_gateway\_jwt\_authorizer\_id) | JWT authorizer ID of the HTTP API created for the dev environment routed backend baseline. |
| <a name="output_api_gateway_request_authorizer_ids"></a> [api\_gateway\_request\_authorizer\_ids](#output\_api\_gateway\_request\_authorizer\_ids) | Map of logical Lambda request authorizer name to HTTP API authorizer ID for the dev environment routed backend baseline. |
| <a name="output_api_gateway_route_ids"></a> [api\_gateway\_route\_ids](#output\_api\_gateway\_route\_ids) | Map of logical route name to route ID for the dev environment routed backend baseline. |
| <a name="output_api_gateway_route_keys"></a> [api\_gateway\_route\_keys](#output\_api\_gateway\_route\_keys) | Map of logical route name to route key for the dev environment routed backend baseline. |
| <a name="output_api_gateway_stage_invoke_url"></a> [api\_gateway\_stage\_invoke\_url](#output\_api\_gateway\_stage\_invoke\_url) | Stage-qualified invoke URL of the HTTP API created for the dev environment routed backend baseline. |
| <a name="output_api_gateway_stage_name"></a> [api\_gateway\_stage\_name](#output\_api\_gateway\_stage\_name) | Stage name of the HTTP API created for the dev environment routed backend baseline. |
| <a name="output_cloudfront_distribution_arn"></a> [cloudfront\_distribution\_arn](#output\_cloudfront\_distribution\_arn) | ARN of the CloudFront distribution created for the dev environment. |
| <a name="output_cloudfront_distribution_domain_name"></a> [cloudfront\_distribution\_domain\_name](#output\_cloudfront\_distribution\_domain\_name) | Domain name of the CloudFront distribution created for the dev environment. |
| <a name="output_cloudfront_distribution_hosted_zone_id"></a> [cloudfront\_distribution\_hosted\_zone\_id](#output\_cloudfront\_distribution\_hosted\_zone\_id) | Route 53 hosted zone ID used by the CloudFront distribution created for the dev environment. |
| <a name="output_cloudfront_distribution_id"></a> [cloudfront\_distribution\_id](#output\_cloudfront\_distribution\_id) | ID of the CloudFront distribution created for the dev environment. |
| <a name="output_cloudfront_s3_origin_access_control_id"></a> [cloudfront\_s3\_origin\_access\_control\_id](#output\_cloudfront\_s3\_origin\_access\_control\_id) | ID of the Origin Access Control used by the dev CloudFront distribution for the private S3 frontend origin. |
| <a name="output_cloudfront_spa_rewrite_function_arn"></a> [cloudfront\_spa\_rewrite\_function\_arn](#output\_cloudfront\_spa\_rewrite\_function\_arn) | ARN of the CloudFront Function that rewrites eligible /app SPA navigations for the dev environment. |
| <a name="output_cloudfront_spa_rewrite_function_name"></a> [cloudfront\_spa\_rewrite\_function\_name](#output\_cloudfront\_spa\_rewrite\_function\_name) | Name of the CloudFront Function that rewrites eligible /app SPA navigations for the dev environment. |
| <a name="output_cognito_admin_group_name"></a> [cognito\_admin\_group\_name](#output\_cognito\_admin\_group\_name) | Name of the Cognito admin group created for the dev environment. |
| <a name="output_cognito_issuer"></a> [cognito\_issuer](#output\_cognito\_issuer) | JWT issuer URL for the Cognito User Pool created for the dev environment. |
| <a name="output_cognito_user_pool_arn"></a> [cognito\_user\_pool\_arn](#output\_cognito\_user\_pool\_arn) | ARN of the Cognito User Pool created for the dev environment. |
| <a name="output_cognito_user_pool_client_id"></a> [cognito\_user\_pool\_client\_id](#output\_cognito\_user\_pool\_client\_id) | ID of the Cognito User Pool Client created for the dev environment. |
| <a name="output_cognito_user_pool_endpoint"></a> [cognito\_user\_pool\_endpoint](#output\_cognito\_user\_pool\_endpoint) | Endpoint of the Cognito User Pool created for the dev environment. |
| <a name="output_cognito_user_pool_id"></a> [cognito\_user\_pool\_id](#output\_cognito\_user\_pool\_id) | ID of the Cognito User Pool created for the dev environment. |
| <a name="output_events_table_arn"></a> [events\_table\_arn](#output\_events\_table\_arn) | ARN of the DynamoDB events table created for the dev environment. |
| <a name="output_events_table_name"></a> [events\_table\_name](#output\_events\_table\_name) | Name of the DynamoDB events table created for the dev environment. |
| <a name="output_frontend_bucket_arn"></a> [frontend\_bucket\_arn](#output\_frontend\_bucket\_arn) | ARN of the private frontend origin bucket created for the dev environment. |
| <a name="output_frontend_bucket_id"></a> [frontend\_bucket\_id](#output\_frontend\_bucket\_id) | ID of the private frontend origin bucket created for the dev environment. |
| <a name="output_frontend_bucket_name"></a> [frontend\_bucket\_name](#output\_frontend\_bucket\_name) | Name of the private frontend origin bucket created for the dev environment. |
| <a name="output_frontend_bucket_regional_domain_name"></a> [frontend\_bucket\_regional\_domain\_name](#output\_frontend\_bucket\_regional\_domain\_name) | Regional domain name of the private frontend origin bucket created for the dev environment. |
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
| <a name="output_waf_web_acl_arn"></a> [waf\_web\_acl\_arn](#output\_waf\_web\_acl\_arn) | ARN of the CloudFront-scoped Web ACL created for the dev environment. |
| <a name="output_waf_web_acl_id"></a> [waf\_web\_acl\_id](#output\_waf\_web\_acl\_id) | ID of the CloudFront-scoped Web ACL created for the dev environment. |
| <a name="output_waf_web_acl_name"></a> [waf\_web\_acl\_name](#output\_waf\_web\_acl\_name) | Name of the CloudFront-scoped Web ACL created for the dev environment. |
<!-- END_TF_DOCS -->
