# AWS Serverless Events Platform

[![Terraform Validation](https://github.com/Mazdaratti/tf-template-stack/actions/workflows/terraform-validation.yml/badge.svg)](https://github.com/Mazdaratti/tf-template-stack/actions/workflows/terraform-validation.yml)
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

### Current focus

- Notification sender, SES strategy, and participant email delivery

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
  - split IAM roles prepared for `notification-planner` and `notification-sender`
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
  - terraform-docs documentation workflow

### Next milestones

- Notification planner/sender workers and SES participant notifications
- Observability baseline
- Remote Terraform backend + GitHub OIDC
- deployment workflow automation beyond Terraform validation

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
15. The participant notification path is planned as:

`EventBridge -> notification-dispatch SQS -> notification-planner Lambda -> notification-email SQS -> notification-sender Lambda -> SES`

16. The deployed `notification-planner` creates one recipient-level email job
per authenticated RSVP user for event update and cancellation notifications.
17. The planned `notification-sender` resolves the current recipient email
through Cognito at send time using the canonical user identity and sends
participant email through **Amazon SES**.

The planner and sender execution roles are provisioned separately with
least-privilege IAM.

Participant emails are user-facing product emails, not admin/debug messages.
The planner produces safe recipient-level jobs, and the sender owns final
presentation through stable templates.

The v1 event-management domain events are:

- `event.created`
- `event.updated`
- `event.cancelled`

EventBridge owns fanout, and notification publication or delivery failures must
not change the original synchronous API result.

### Observability

18. Logs and metrics are collected in **Amazon CloudWatch**.
19. Distributed tracing is enabled with **AWS X-Ray** to analyze request performance and dependencies.

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

Infrastructure is initially developed using local state for rapid iteration.  
Remote backend and deployment automation will be introduced later.

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
|       `-- ci.yml
|
|-- docs/
|   |-- assets/
|   |-- architecture.md
|   |-- local-setup.md
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
|   |-- index.html
|   |-- package-lock.json
|   |-- package.json
|   |-- tsconfig.json
|   `-- vite.config.ts
|
|-- infrastructure/
|   |-- bootstrap/
|   |   `-- dev/
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
|       |-- s3_frontend_bucket/
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
   - implement `notification-sender` to consume `notification-email` messages
   - resolve current recipient email at send time through Cognito
   - render user-facing participant email content through stable sender
     templates
   - send participant emails through SES
   - keep user-facing API responses independent from notification delivery

21. CloudWatch observability and X-Ray tracing
   - add production-oriented logs, metrics, tracing, and validation evidence

22. Remote Terraform backend and GitHub OIDC
   - introduce remote Terraform state
   - add GitHub Actions AWS authentication through OIDC
   - keep this separate from application deployment workflows

23. CI validation workflow hardening
   - keep CI read-only and validation-focused
   - add frontend validation to CI:
     - `npm ci`
     - `npm run typecheck`
     - `npm run build`
   - keep Terraform validation detached from real AWS state
   - do not deploy from CI validation jobs

24. CI/CD deployment workflows
   - add separate provisioning and deployment workflows after OIDC exists
   - keep provisioning responsible for Terraform infrastructure changes
   - keep deployment responsible for application artifacts
   - add frontend deployment workflow for S3 sync and CloudFront invalidation
   - keep Lambda deployment Terraform-managed initially

25. Optional Lambda code deployment separation
   - prepare for a future model where Terraform creates Lambda shell/config
   - move Lambda ZIP artifact publishing to deployment automation
   - update Lambda code with `aws lambda update-function-code`
   - keep IAM, environment variables, log groups, and API wiring in Terraform
   - add versions/aliases only after the basic split is validated


The repository now also includes Terraform validation coverage for the currently
implemented modules, examples, and `envs/dev` root, focused Python validation
for the implemented Lambda handlers and shared auth flow, and frontend CI
validation for typechecking, production builds, component tests, and browser
smoke tests.

This improves static validation confidence while real AWS behavior continues to
be verified through local `plan`, `apply`, and milestone-specific routed API
validation in the dev environment.

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

Detailed architecture description:

- `docs/architecture.md`
- `docs/platform-behavior.md`
- `docs/local-setup.md`
- `infrastructure/envs/dev/README.md`
- each module also contains its own `README.md` in the module root directory

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

- `docs/local-setup.md`

---

## Future Improvements

- Custom domain and TLS configuration
- Monitoring dashboards and alerting
- Automated frontend deployment
- Multi-environment promotion strategy
- Advanced security hardening
