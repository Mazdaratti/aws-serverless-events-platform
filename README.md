# AWS Serverless Events Platform

[![CI Validation](https://github.com/Mazdaratti/aws-serverless-events-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/Mazdaratti/aws-serverless-events-platform/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

A production-style, fully AWS-native serverless web application for managing events and RSVP workflows.

The system demonstrates modern cloud architecture patterns including transactional serverless writes, event-driven extensions, managed authentication, edge security, and Infrastructure as Code using Terraform.

This project is designed as a **cloud engineering portfolio showcase** and follows real-world engineering practices such as least-privilege IAM, cost-aware design, incremental delivery, and modular infrastructure composition.

---

## Project Goals

- Build a production-shaped serverless platform using managed AWS services
- Demonstrate **transactional API workflows with asynchronous extensions**
- Apply security best practices (edge protection, managed identity, least privilege)
- Implement observability and operational readiness patterns
- Use Terraform as the single source of infrastructure truth
- Follow clean Git workflow and small, reviewable infrastructure changes
- Stay within AWS Free Tier and promotional credits

---

## Current Development Status

### Completed milestones

- Platform foundations
  - AWS account and repository foundation
  - modular Terraform structure
  - local-state-first `dev` environment
  - architecture and behavior contracts

- Core infrastructure
  - DynamoDB data layer for events and RSVPs
  - SQS queues and DLQs for async notification work:
    - `notification-dispatch`
    - `notification-email`
  - least-privilege IAM roles for deployed Lambda workloads
  - split least-privilege IAM roles for `notification-planner` and
    `notification-sender`
  - separate notification Lambda composition for planner/sender workers
  - ZIP-packaged Lambda deployment baseline
  - Cognito User Pool, app client, and admin group
  - routed API Gateway HTTP API baseline

- Edge and frontend delivery
  - private S3 frontend origin
  - CloudFront distribution as the browser-facing entry point
  - CloudFront Function for `/app` SPA deep-link rewrites
  - API forwarding for `/events` and `/events/*`
  - optional CloudFront-scoped WAF baseline
  - local frontend deployment helper for S3 sync and CloudFront invalidation
  - manual GitHub Actions frontend deployment dry-run workflow validated from
    `main`
  - manual GitHub Actions frontend deployment apply workflow validated from
    `main`

- Routed backend workloads
  - `create-event`
  - `list-events`
  - `list-my-events`
  - `get-event`
  - `update-event`
  - `cancel-event`
  - `rsvp`
  - `get-event-rsvps`
  - `rsvp-authorizer`

- Async notification foundation
  - EventBridge custom event bus
  - compact post-commit domain events for:
    - `event.created`
    - `event.updated`
    - `event.cancelled`
  - SNS admin notification topic and confirmed dev email subscription
  - EventBridge-routed admin notifications
  - participant dispatch routing to `notification-dispatch` for:
    - `event.updated`
    - `event.cancelled`
  - deployed `notification-planner` worker for participant notification planning
  - `notification-email` queue for recipient-level participant email jobs
  - SES sender identity and participant email templates wired in `dev`
  - deployed `notification-sender` worker for SES templated participant email
    delivery
  - `notification-email` event source mapping with partial batch responses
  - Cognito `sub` lookup at send time for current recipient email resolution
  - EventBridge-to-SNS and EventBridge-to-SQS policies hardened with source ARN
    and `aws:SourceAccount`
  - synchronous API outcomes remain independent from async notification delivery

- Frontend application
  - React + Vite + TypeScript SPA under `/app`
  - same-origin API client using `/events` paths
  - Cognito auth with sessionStorage token handling
  - public event listing and detail pages
  - mixed-mode RSVP UI
  - authenticated create, edit, cancel, my-events, and RSVP-list flows
  - responsive Tailwind CSS UI
  - route-level lazy loading
  - accessibility and user-feedback baseline

- Validation and developer workflow
  - Python Lambda tests
  - frontend Vitest and Playwright tests
  - Terraform module/example/dev validation in CI
  - frontend CI validation for install, typecheck, build, component tests, and
    browser smoke tests
  - deterministic Lambda ZIP packaging helper
  - CI concurrency and job timeouts for stale-run and stuck-job protection
  - CI syntax compilation for repository helper scripts
  - terraform-docs documentation workflow

- Observability baseline
  - Lambda X-Ray active tracing enabled for all deployed `dev` Lambda workloads
  - minimal X-Ray write permissions added to Lambda execution policies
  - representative trace generation validated in AWS X-Ray
  - reusable CloudWatch observability module added for alarms and dashboard
  - CloudWatch metric alarms wired into `dev` for Lambda, API Gateway, SQS, and
    EventBridge
  - compact CloudWatch dashboard wired into `dev`
  - alert delivery intentionally disabled with empty alarm and OK actions
  - CloudWatch observability validation completed in AWS

- Remote backend and GitHub OIDC bootstrap
  - reusable persistent remote backend module baseline
  - teardown-friendly `dev` bootstrap root
  - generated Git-ignored `infrastructure/envs/dev/backend.tf`
  - S3 backend bucket with versioning, SSE-S3 encryption, public access block,
    and `BucketOwnerEnforced`
  - S3 native lockfile backend configuration
  - GitHub Actions OIDC provider
  - branch-scoped GitHub Actions IAM role for `main`
  - separate Terraform state access policy
  - split serverless deploy policies for the current platform surface
  - repo-aligned permissions boundary
  - AWS bootstrap validation completed for `dev`
  - `infrastructure/envs/dev` migrated to the generated S3 backend
  - remote-backed `dev` Terraform plan validated clean
  - unified repository variable and secret sync helper added for GitHub Actions
    provisioning inputs
  - GitHub repository variables and secrets can be synced from bootstrap outputs
    and local dev Terraform inputs
  - manual AWS OIDC smoke workflow added for branch-scoped role validation
  - GitHub Actions OIDC smoke workflow validated successfully from `main`

- Provisioning dry-run automation
  - manual GitHub Actions provisioning dry-run workflow added
  - workflow packages Lambda ZIP artifacts before Terraform planning
  - workflow runs Terraform init, validate, and plan through GitHub OIDC
  - workflow validated successfully from `main` with a clean Terraform plan
  - OIDC deploy policy includes Terraform refresh read permissions required by
    the current `dev` platform surface
  - workflow does not run Terraform apply
  - workflow does not deploy Lambda code or frontend assets

- Provisioning apply automation
  - manual GitHub Actions provisioning apply workflow added
  - workflow requires explicit `confirm_apply=apply-dev` confirmation
  - workflow packages Lambda ZIP artifacts before Terraform planning
  - workflow runs Terraform init, validate, plan, and apply through GitHub OIDC
  - workflow applies the saved Terraform plan
  - workflow validated successfully from `main`
  - workflow does not deploy Lambda code or frontend assets

- Lambda deployment dry-run automation
  - reusable Lambda deployment helper added with dry-run and apply modes
  - manual GitHub Actions Lambda deployment dry-run workflow added
  - workflow packages Lambda ZIP artifacts through the real packaging path
  - workflow validates deployed workload-to-function mapping from Terraform
    outputs
  - workflow previews planned `aws lambda update-function-code` commands
  - workflow validated successfully from `main`
  - workflow does not run Terraform plan/apply
  - workflow does not update Lambda code or deploy frontend assets

- Lambda deployment apply automation
  - manual GitHub Actions Lambda deployment apply workflow added
  - workflow requires explicit `confirm_deploy=deploy-lambdas-dev`
    confirmation
  - workflow packages Lambda ZIP artifacts through the real packaging path
  - workflow validates deployed workload-to-function mapping from Terraform
    outputs
  - workflow updates existing Lambda function code with
    `aws lambda update-function-code --no-publish`
  - workflow validated successfully from `main`
  - workflow does not run Terraform plan/apply or deploy frontend assets

---

## Target Architecture

The platform uses native AWS serverless services:

- Amazon CloudFront
- AWS WAF
- Amazon S3
- Amazon API Gateway
- AWS Lambda
- Amazon DynamoDB
- Amazon Cognito
- Amazon SQS
- Amazon EventBridge
- Amazon SNS
- Amazon SES
- Amazon CloudWatch
- AWS X-Ray

AWS Shield Standard provides automatic edge protection.

---

## Target System Workflow

### Frontend Delivery

1. Users access the application through **Amazon CloudFront**.
2. CloudFront securely serves static frontend assets from a private **Amazon S3** bucket.
3. Frontend browser routes are served under `/app`.
4. **AWS WAF** can filter malicious traffic at the edge before requests reach the backend when enabled for the environment.

### Frontend Routing Model

The frontend is delivered as a SPA under:

- `/app`

API routes remain under:

- `/events`

CloudFront handles SPA deep-link routing for `/app/*` without affecting API behavior.

### API Request Flow

5. The frontend sends same-origin API requests through **Amazon CloudFront** to **Amazon API Gateway**.
6. Route protection is enforced at API Gateway using a hybrid authorizer model:
   - native JWT authorizer for ordinary protected routes
   - a dedicated Lambda authorizer for the mixed-mode RSVP route

### Event Management

7. API Gateway invokes a **Lambda function** to create or retrieve event data.
8. Event information is stored in **Amazon DynamoDB**, providing scalable serverless persistence.

### RSVP Processing

9. RSVP submissions are handled as a **synchronous business operation**.
10. The primary RSVP write path is:

`Client -> CloudFront -> API Gateway -> Lambda -> DynamoDB transaction`

11. This design preserves the current API contract so the caller immediately knows whether:
- the RSVP was created
- the RSVP was updated
- the event is already at capacity
- access is forbidden
- the event does not exist

### Event-Driven Extensions

12. After a successful durable event-management write, one compact domain event
is published to **Amazon EventBridge**.
13. EventBridge routes admin notifications directly to an **Amazon SNS** admin
topic. In the current direct-SNS baseline, EventBridge input transformers
provide lightweight admin email formatting with the full CloudFront event URL.
14. EventBridge routes participant-notification planning work to **Amazon SQS**.
15. The participant notification path is:

`EventBridge -> notification-dispatch SQS -> notification-planner Lambda -> notification-email SQS -> notification-sender Lambda -> SES`

16. The deployed `notification-planner` creates one recipient-level email job
per authenticated RSVP user for event update and cancellation notifications.
17. The SES baseline provides the sender identity and reusable participant email
templates for update and cancellation notifications.
18. The deployed `notification-sender` consumes recipient-level jobs from
`notification-email`, resolves the current recipient email through Cognito at
send time, selects the SES template, provides safe template data, and sends
participant email through **Amazon SES**.

The planner and sender execution roles are provisioned separately with
least-privilege IAM.

Participant emails are user-facing product emails, not admin/debug messages.
The planner produces safe recipient-level jobs. SES owns reusable template
definitions, and the sender owns template selection, safe template data, and
delivery.

In `dev`, SES uses a verified project sender inbox and sandbox-verified
recipient addresses. Production-shaped deliverability improvements such as a
custom domain identity, DKIM, SPF, DMARC, and MAIL FROM configuration remain
future email-deliverability work.

The v1 event-management domain events are:

- `event.created`
- `event.updated`
- `event.cancelled`

EventBridge owns fanout, and notification publication or delivery failures must
not change the original synchronous API result.

### Observability

19. Logs and metrics are collected in **Amazon CloudWatch**.
20. **AWS X-Ray** active tracing is enabled for deployed Lambda workloads in
`dev` to analyze request performance and dependencies.
21. CloudWatch metric alarms are deployed for Lambda errors/throttles, API
Gateway 5xx responses, SQS queue depth/age/DLQ depth, and EventBridge failed
invocations.
22. A compact CloudWatch dashboard is deployed for Lambda, API Gateway, SQS,
and EventBridge runtime visibility.

API Gateway active tracing is not enabled because the platform uses API Gateway
HTTP API, while API Gateway active tracing applies to REST APIs.

CloudWatch alarm actions are intentionally empty in `dev`; alert routing is
kept separate from the first metric coverage baseline.

This design preserves immediate correctness for core business writes while still enabling scalable asynchronous processing where it adds real value.

---

## Key Architecture Decisions

**Fully Serverless Design**

Avoids infrastructure management and enables automatic scaling.

**Synchronous Core, Async Extensions**

Core business writes are intentionally kept synchronous so the system can
preserve immediate business-result semantics required by the current API
contract.

Asynchronous processing is reserved for durable post-commit work. EventBridge
owns notification fanout, SNS handles admin broadcasts, and SQS buffers
participant-notification work outside the primary API write path.

**Managed Authentication**

Amazon Cognito replaces custom authentication logic, improving security and reducing operational overhead.

The routed API uses a hybrid authorizer model so ordinary protected routes stay
simple while the RSVP route can support anonymous and authenticated callers on
one business operation.

**No VPC Architecture**

Simplifies networking and keeps costs low while still supporting production-grade patterns.

**Local Terraform State First**

Infrastructure started with local Terraform state for rapid iteration while
the platform shape was still changing quickly.

The `dev` environment uses an S3 remote backend created by the bootstrap root.
Its backend configuration is generated into `infrastructure/envs/dev/backend.tf`.
Terraform state uses S3 native lockfile support enabled through
`use_lockfile = true`, while deployment automation remains separate from infrastructure state management. 

**Modular Terraform Design**

Reusable infrastructure logic is implemented in focused Terraform modules, while `infrastructure/envs/dev` stays thin and composition-oriented.

This keeps changes reviewable, reduces refactoring churn, and supports future multi-environment expansion.

**Incremental Module Hardening**

Infrastructure slices may begin as environment-driven compositions while the
required behavior is being proven in real AWS.

Once a layer is validated end to end, its reusable module is tightened,
documented, example-backed, and CI-validated before the next major platform
layer is introduced.

This allows delivery to stay incremental without leaving temporary module
assumptions in place longer than necessary.

---

## Repository Structure

```text
aws-serverless-events-platform/
|
|-- .github/
|   `-- workflows/
|       |-- aws-oidc-smoke.yml
|       |-- frontend-deploy-dry-run.yml
|       |-- frontend-deploy-apply.yml
|       |-- provisioning-dry-run.yml
|       |-- provisioning-apply.yml
|       |-- lambda-deploy-dry-run.yml
|       |-- lambda-deploy-apply.yml
|       `-- ci.yml
|
|-- docs/
|   |-- assets/
|   |-- architecture.md
|   |-- project-setup.md
|   `-- platform-behavior.md
|
|-- frontend/
|   |-- public/
|   |   `-- favicon.ico
|   |-- src/
|   |   |-- api/
|   |   |-- auth/
|   |   |-- components/
|   |   |-- routes/
|   |   |-- utils/
|   |   |-- App.tsx
|   |   |-- main.tsx
|   |   `-- styles.css
|   |-- .env.example
|   |-- README.md
|   |-- index.html
|   |-- package-lock.json
|   |-- package.json
|   |-- tsconfig.json
|   `-- vite.config.ts
|
|-- infrastructure/
|   |-- bootstrap/
|   |   `-- dev/
|   |       |-- README.md
|   |       |-- artifacts.tf
|   |       |-- github_oidc.tf
|   |       |-- locals.tf
|   |       |-- outputs.tf
|   |       |-- policy_boundary.tf
|   |       |-- policy_deploy.tf
|   |       |-- policy_state.tf
|   |       |-- providers.tf
|   |       |-- remote_backend.tf
|   |       |-- terraform.tfvars.example
|   |       |-- variables.tf
|   |       `-- versions.tf
|   |
|   |-- envs/
|   |   `-- dev/
|   |       |-- README.md
|   |       |-- data.tf
|   |       |-- locals.tf
|   |       |-- main.tf
|   |       |-- outputs.tf
|   |       |-- providers.tf
|   |       |-- resource_policies.tf
|   |       |-- terraform.tfvars.example
|   |       |-- variables.tf
|   |       `-- versions.tf
|   |
|   `-- modules/
|       |-- api_gateway/
|       |-- cloudfront/
|       |-- cognito/
|       |-- dynamodb_data_layer/
|       |-- eventbridge/
|       |-- iam/
|       |-- lambda/
|       |-- observability/
|       |-- remote_backend/
|       |-- s3_frontend_bucket/
|       |-- ses/
|       |-- sns/
|       |-- sqs/
|       `-- waf/
|
|-- lambdas/
|   `-- Python Lambda workload source folders, shared helpers, and authorizer code
|
|-- scripts/
|   `-- Python helper scripts for packaging and local build workflows
|
|-- tests/
|   `-- Focused automated tests for implemented Lambda handlers, shared auth logic, and related workflows
|
|-- .gitignore
|-- .terraform-docs.yml
|-- LICENSE
`-- README.md
```

Infrastructure is implemented using modular Terraform design with environment-specific composition.

---

## Infrastructure Implementation Roadmap

1. Terraform environment foundation ✅
   - local-state-first `envs/dev` baseline ✅
   - provider/version constraints ✅
   - shared naming and tagging structure ✅

2. DynamoDB business data layer ✅
   - `events` table ✅
   - `rsvps` table ✅
   - initial event listing GSIs ✅

3. SQS queues and dead-letter queues ✅
   - notification dispatch queue ✅
   - notification email queue ✅
   - dedicated DLQ wiring for both notification queues ✅

4. IAM roles and policies for workloads ✅
   - least-privilege execution roles ✅
   - workload-specific access profiles ✅
   - DynamoDB and SQS policy wiring ✅
   - split notification planner/sender IAM roles ✅

5. Lambda compute layer ✅
   - ZIP-based Lambda deployment baseline ✅
   - external packaging workflow ✅
   - CloudWatch log group wiring ✅

6. Core synchronous Lambda workload rollout ✅
   - `create-event` ✅
   - `list-events` ✅
   - `list-my-events` ✅
   - `get-event` ✅
   - `update-event` ✅
   - `cancel-event` ✅
   - `rsvp` ✅
   - `get-event-rsvps` ✅

7. Cognito authentication baseline ✅
   - Cognito User Pool ✅
   - public app client ✅
   - admin group ✅

8. Lambda identity normalization across authorizer modes ✅
   - shared caller normalization helper ✅
   - shared helper test coverage ✅
   - shared packaging support for `shared/...` imports ✅
   - `create-event` normalization adoption ✅
   - `update-event` normalization adoption ✅
   - `cancel-event` normalization adoption ✅
   - `get-event-rsvps` normalization adoption ✅
   - `rsvp` normalization adoption ✅
   - `list-events` public-only cleanup ✅

9. `list-my-events` workload split from `list-events` ✅
   - dedicated creator-scoped listing workload ✅
   - JWT-protected routed path ✅

10. Mixed-mode RSVP Lambda authorizer ✅
   - mixed anonymous/authenticated caller projection ✅
   - invalid presented auth denied at API Gateway edge ✅
   - routed downstream shape validated in AWS ✅

11. Routed API rollout and AWS validation ✅
   - `create-event` routed path ✅
   - `update-event` routed path ✅
   - `cancel-event` routed path ✅
   - `get-event-rsvps` routed path ✅
   - `list-events` routed path ✅
   - `list-my-events` routed path ✅
   - `get-event` routed path ✅
   - `rsvp` routed path ✅
   - temporary RSVP probe slice removed after real route validation ✅

12. API Gateway reusable module completion and hardening ✅
   - hardened the module interface ✅
   - tightened variable validation and module assumptions ✅
   - improved descriptions and comments ✅
   - added `examples/basic_usage` ✅
   - added module `README.md` ✅
   - ensured `terraform-docs` injection is correct ✅
   - expanded Terraform validation CI to cover the module and example ✅

13. Edge delivery layer (S3 + CloudFront + WAF)
   - `s3_frontend_bucket` reusable module baseline ✅
   - `infrastructure/envs/dev` wiring for the private frontend origin bucket ✅
   - `waf` reusable module ✅
   - `infrastructure/envs/dev` wiring for the WAF baseline ✅
   - `cloudfront` reusable module ✅
   - `infrastructure/envs/dev` wiring for the CloudFront baseline ✅
   - `/app` SPA routing namespace and CloudFront Function rewrite ✅

14. Frontend Foundation ✅
15. Frontend Product Functionality Layer ✅
16. Frontend Deployment Integration ✅
   - local/manual frontend deployment path ✅
   - read required public frontend values from Terraform outputs ✅
   - build the React/Vite frontend with public `VITE_*` values only ✅
   - sync `frontend/dist/` to the private S3 frontend bucket ✅
   - invalidate CloudFront after frontend artifact upload ✅
   - keep CloudFront as the only browser-facing entry point ✅
   - no backend, Lambda, API Gateway, or routing behavior changes ✅

17. Frontend UX + Performance Hardening ✅
   - Tailwind CSS v4 baseline ✅
   - reusable layout primitives ✅
   - responsive page and shared component migration ✅
   - shared event list controls with public vs owner option sets ✅
   - accessibility pass for skip links, forms, status feedback, lists, and
     destructive confirmation ✅
   - route-level lazy loading ✅
   - production bundle output review ✅
   - CloudFront deployment and manual browser validation ✅
   - no backend, API route, Terraform, or deployment-helper behavior changes ✅

18. Frontend Automated Testing Baseline
   - Vitest + React Testing Library baseline ✅
   - Playwright browser smoke baseline ✅
   - CI frontend test integration / coverage expansion ✅

19. EventBridge, SNS admin notifications, and SQS fanout
   - add reusable EventBridge module baseline ✅
   - add SNS admin notification topic baseline ✅
   - wire EventBridge bus and SNS admin notification topic for `dev` ✅
   - wire EventBridge routing for `dev` ✅
   - route `event.created`, `event.updated`, and `event.cancelled` to the SNS
     admin topic ✅
   - route `event.updated` and `event.cancelled` to the existing
     `notification-dispatch` SQS queue ✅
   - add SNS and SQS resource policies scoped to concrete EventBridge rule
     ARNs ✅
   - add `aws:SourceAccount` hardening to EventBridge-to-SNS and
     EventBridge-to-SQS resource policies ✅
   - add least-privilege EventBridge publishing permissions for write Lambdas ✅
   - wire EventBridge bus-name environment variable for write Lambdas ✅
   - publish `event.cancelled` from `cancel-event` after successful durable
     cancellation, with tests and validation ✅
   - publish `event.created` from `create-event` after successful durable
     creation, with tests and validation ✅
   - publish `event.updated` from `update-event` after successful durable
     update, with tests and validation ✅
   - add configurable dev admin SNS email subscription without hardcoded
     personal email addresses ✅
   - confirm the admin SNS email subscription ✅
   - add admin SNS message formatting through EventBridge input transformers ✅
   - validate end-to-end admin email delivery for `event.created`,
     `event.updated`, and `event.cancelled` ✅
   - keep synchronous API outcomes independent from async notification results

20. Notification planner/sender workers and SES participant notifications
   - add `notification-email` SQS queue and DLQ ✅
   - harden `notification-dispatch` queue timing for future Lambda SQS
     consumption ✅
   - add least-privilege IAM for `notification-planner` ✅
   - add least-privilege IAM for `notification-sender` ✅
   - implement `notification-planner` to consume `notification-dispatch`
     messages ✅
   - query RSVP records by event and enqueue one recipient-level email job per
     authenticated RSVP user ✅
   - include both attending and not-attending RSVP users ✅
   - skip anonymous RSVP subjects in v1 ✅
   - wire `notification-planner` into `infrastructure/envs/dev` with an SQS
     event source mapping and partial batch responses ✅
   - add reusable SES sender identity and participant template module ✅
   - add reusable SES module example and CI validation coverage ✅
   - wire SES sender identity and templates into `infrastructure/envs/dev` ✅
   - configure the dedicated project sender inbox through local untracked
     tfvars ✅
   - manually verify the dedicated project sender inbox in SES ✅
   - split notification Lambda deployment composition so sender can use the
     CloudFront distribution domain without introducing a dependency cycle ✅
   - implement `notification-sender` to consume `notification-email` messages ✅
   - wire `notification-sender` into `infrastructure/envs/dev` with an SQS
     event source mapping and partial batch responses ✅
   - resolve current recipient email at send time through Cognito `ListUsers`
     by canonical `sub` ✅
   - select SES templates and provide safe text/HTML template data ✅
   - scope sender IAM to `notification-email`, Cognito user lookup, and SES
     templated sending from the project sender identity ✅
   - send templated participant emails through SES ✅
   - add notification sender unit tests and CI compile coverage ✅
   - keep user-facing API responses independent from notification delivery ✅

21. CloudWatch observability and X-Ray tracing
   - Lambda X-Ray active tracing baseline ✅
     - add optional Lambda `tracing_mode` support in the reusable Lambda module ✅
     - enable `tracing_mode = "Active"` for all deployed `dev` Lambda workloads ✅
     - add minimal X-Ray write permissions to Lambda execution policies ✅
     - validate representative trace generation in AWS X-Ray ✅
   - CloudWatch alarm baseline ✅
     - add reusable observability module ✅
     - add high-signal Lambda errors and throttles alarms ✅
     - add SQS source queue depth, DLQ depth, and oldest-message-age alarms ✅
     - add API Gateway 5xx alarm ✅
     - add EventBridge failed-invocation alarms ✅
     - wire alarms into `infrastructure/envs/dev` with alert actions disabled ✅
     - validate 32 deployed CloudWatch metric alarms in AWS ✅
   - compact CloudWatch dashboard ✅
     - include Lambda, API Gateway, SQS, and EventBridge panels ✅
     - wire the dashboard into `infrastructure/envs/dev` ✅
     - validate the deployed dashboard in AWS ✅
   - alert delivery and advanced telemetry deferred ✅
     - no SNS alert topic creation in the first alarm baseline ✅
     - no log metric filters in the first alarm baseline ✅
     - no SES, CloudFront, WAF, cost, or X-Ray dashboard widgets in this slice ✅
     - no ADOT/OpenTelemetry or Powertools tracing instrumentation yet ✅

22. Remote Terraform backend and GitHub OIDC
   - add reusable remote Terraform backend module baseline ✅
   - add teardown-friendly `infrastructure/bootstrap/dev` root ✅
   - generate ignored `infrastructure/envs/dev/backend.tf` for the S3 backend ✅
   - configure S3 native lockfile state locking with `use_lockfile = true` ✅
   - create the dev backend bucket with versioning, SSE-S3 encryption, public
     access block, and `BucketOwnerEnforced` ✅
   - create GitHub Actions OIDC provider and branch-scoped IAM role ✅
   - attach separate state access and split deploy policies to the OIDC role ✅
   - add a repo-aligned permissions boundary for the OIDC role ✅
   - validate the bootstrap resources in AWS ✅
   - migrate `infrastructure/envs/dev` to remote state ✅
   - validate a clean remote-backed `dev` Terraform plan ✅
   - add unified repository variable and secret sync helper for GitHub Actions
     provisioning inputs ✅
   - support syncing GitHub repository variables and secrets from bootstrap
     outputs and local dev Terraform inputs ✅
   - add manual GitHub Actions OIDC smoke workflow ✅
   - validate GitHub Actions OIDC smoke workflow from `main` ✅
   - keep application deployment workflows separate from this infrastructure
     bootstrap

23. CI validation workflow hardening
   - keep CI read-only and validation-focused ✅
   - add frontend validation to CI:
     - `npm ci` ✅
     - `npm run typecheck` ✅
     - `npm run build` ✅
     - `npm run test` ✅
     - `npm run test:e2e` ✅
   - add workflow concurrency to cancel stale branch and PR runs ✅
   - add job timeouts for Terraform, Lambda, frontend, and Terraform matrix
     validation ✅
   - compile repository helper scripts in CI ✅
   - keep Terraform validation detached from real AWS state ✅
   - do not deploy from CI validation jobs ✅
   - validate hardened CI workflow successfully ✅

24. Frontend deployment workflows
   - establish manual GitHub Actions deployment workflows after OIDC exists ✅
   - keep CI validation separate from deployment workflows ✅
   - add manual frontend deployment dry-run workflow ✅
   - validate frontend deployment dry-run workflow from `main` ✅
   - add frontend deployment apply workflow for S3 sync and CloudFront
     invalidation ✅
   - validate frontend deployment apply workflow from `main` ✅
   - keep Terraform provisioning, Lambda packaging, and Lambda code deployment
     outside frontend deployment workflows ✅

25. Lambda provisioning and code deployment separation
   - define the ownership boundary between Terraform and deployment automation ✅
     - Terraform owns Lambda infrastructure, runtime, handler, memory, timeout,
       tracing, IAM, environment variables, log groups, API Gateway
       integrations, Lambda permissions, SQS event source mappings, and related
       AWS service wiring
     - automation owns Lambda ZIP artifact packaging for provisioning and code
       deployment workflows
     - Lambda code deployment automation owns existing-function code updates
     - Terraform plans must still detect real infrastructure/configuration drift
     - external code-only Lambda updates must not cause Terraform to plan a code
       rollback ✅
   - establish reusable Lambda packaging for both automation lanes ✅
     - package all deployed Lambda workloads into `artifacts/lambda/`
     - reuse the same packaging path for provisioning and future code deployment
     - handle the RSVP authorizer vendor build requirement
   - add provisioning automation for Terraform validation ✅
     - sync required GitHub repository variables and secrets for provisioning
     - package Lambda ZIP artifacts before Terraform planning
     - run Terraform init, validate, and plan from GitHub Actions
     - validate the provisioning dry-run workflow from `main` with a clean
       Terraform plan
   - add provisioning apply automation ✅
     - run Terraform plan/apply manually from GitHub Actions ✅
     - require explicit confirmation before applying infrastructure changes ✅
     - apply the saved Terraform plan ✅
     - validate provisioning apply workflow from `main` ✅
     - do not deploy Lambda code directly through `update-function-code` ✅
     - do not deploy frontend assets ✅
   - add Lambda code deployment automation
     - add reusable Lambda deployment helper with dry-run/apply modes ✅
     - add manual Lambda deployment dry-run workflow ✅
     - package Lambda ZIP artifacts ✅
     - map workload keys to deployed Lambda function names ✅
     - validate Lambda deployment dry-run workflow from `main` ✅
     - add manual Lambda deployment apply workflow ✅
     - update existing Lambda function code with
       `aws lambda update-function-code`
     - validate Lambda deployment apply workflow from `main` ✅
     - do not run Terraform apply for code-only deployments
     - do not deploy frontend assets
26. Account lifecycle and Cognito account-management UX
   - docs-first account lifecycle contract
     - lock self-service account lifecycle semantics before implementation
     - decide how account deletion affects owned events, RSVP records,
       notifications, and future audit/history behavior
     - decide whether v1 should support deletion, disablement, anonymization,
       or a staged workflow
     - keep Cognito as the identity provider while platform-specific data
       cleanup remains an application responsibility
   - Cognito self-service account UI
     - add or harden frontend account-management screens
     - support user-facing Cognito flows such as password reset, password
       change, email verification, and session cleanup where appropriate
     - keep frontend identity behavior aligned with Cognito and the existing
       sessionStorage token rule
   - platform-controlled account deletion workflow
     - add backend API support only after the account lifecycle contract is
       locked
     - handle app-owned data consistently according to the chosen retention and
       cleanup policy
     - avoid treating Cognito user deletion as the whole product workflow
   - admin account-management workflow
     - defer admin user-management UI until backend admin account APIs exist
     - keep Cognito group membership as the source of admin capability
     - avoid frontend-only admin account management without backend authority

---

## Security Principles

- Least-privilege IAM access
- Optional edge protection using AWS WAF
- Private S3 origin behind CloudFront
- Managed identity via Amazon Cognito
- Failure isolation using SQS dead-letter queues where asynchronous processing is used

---

## Cost Awareness

The system is designed to operate within:

- AWS promotional credits
- Always-free service limits

No EC2 instances, NAT Gateways, or relational databases are used.
In `dev`, WAF is disabled by default until active frontend traffic justifies the steady Web ACL and rule cost.

---

## Environment Strategy

- Development begins with a single `dev` environment
- Terraform modules allow future multi-environment expansion
- Deployment automation will be added after validating the core platform

---

## Documentation

Project documentation is split by purpose:

- [architecture.md](docs/architecture.md): platform architecture, service
  boundaries, and implementation direction.
- [platform-behavior.md](docs/platform-behavior.md): product/API behavior,
  authorization semantics, and runtime platform contracts.
- [project-setup.md](docs/project-setup.md): setup and operations runbook for
  bootstrap, provisioning, deployment workflows, and local tooling.
- [frontend/README.md](frontend/README.md): frontend validation, runtime
  rules, deployment helper behavior, and CloudFront validation.
- [lambdas/README.md](lambdas/README.md): Lambda packaging, artifact layout, and
  workload-specific packaging notes.
- [infrastructure/envs/dev/README.md](infrastructure/envs/dev/README.md): composed
  `dev` Terraform environment.
- Terraform modules each include a module-specific `README.md` in the module
  root directory.

---

## Developer Tooling

The current local workflow expects:

- Python
- Docker
- Terraform
- `tflint`
- `terraform-docs`
- Node.js
- npm

The frontend implementation uses:

- React + Vite + TypeScript
- React Router with `BrowserRouter` and `/app` as the route basename
- `aws-amplify/auth` for Cognito browser authentication
- plain `fetch` for backend API calls
- Node.js and npm for frontend build tooling

See:

- `docs/project-setup.md`

---

## Future Improvements

- Custom domain and TLS configuration
- Production alert delivery and escalation routing
- Multi-environment promotion and release strategy
- Advanced security hardening
