# AWS Serverless Events Platform

[![CI Validation](https://github.com/Mazdaratti/aws-serverless-events-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/Mazdaratti/aws-serverless-events-platform/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

A production-style, fully AWS-native serverless web application for managing events and RSVP workflows.

The system demonstrates modern cloud architecture patterns including transactional serverless writes, event-driven extensions, managed authentication, edge security, and Infrastructure as Code using Terraform.

This project is designed as a **cloud engineering portfolio showcase** and follows real-world engineering practices such as least-privilege IAM, cost-aware design, incremental delivery, and modular infrastructure composition.

---

## Portfolio Snapshot

This project showcases:

- end-to-end AWS serverless application delivery with CloudFront, API Gateway,
  Lambda, DynamoDB, Cognito, EventBridge, SQS, SNS, SES, CloudWatch, and X-Ray
- modular Terraform infrastructure with reusable modules, examples, generated
  documentation, and CI validation
- GitHub Actions deployment automation using AWS OIDC instead of long-lived AWS
  credentials
- separated operational lanes for Terraform provisioning, frontend asset
  deployment, and Lambda code deployment
- transactional DynamoDB write paths with asynchronous notification fanout
- React/Vite frontend delivery through a private S3 origin and CloudFront

Showcase visuals:

Current AWS serverless architecture and application workflows:

![AWS Serverless Events Platform architecture](docs/assets/showcase/10-aws-serverless-events-platform-architecture-overview.png)

Development workflows, tooling, and deployment boundaries:

![Development workflows and tooling](docs/assets/showcase/11-development-workflows-and-tooling.png)

Product workflow through CloudFront:

![Event detail and RSVP workflow](docs/assets/showcase/02-product-event-detail-rsvp.png)


CloudWatch operational dashboard:

![CloudWatch observability dashboard](docs/assets/showcase/07-cloudwatch-dashboard.png)

Code-only Lambda deployment through GitHub Actions:

![Lambda deployment apply workflow success](docs/assets/showcase/05-lambda-deploy-apply-success.png)

Additional evidence:

- [Event listing through CloudFront](docs/assets/showcase/01-product-event-list.png)
- [Owner event management view](docs/assets/showcase/03-product-owner-rsvp-list.png)
- [GitHub Actions workflow inventory](docs/assets/showcase/04-github-actions-workflows.png)
- [Provisioning apply workflow success](docs/assets/showcase/06-provisioning-apply-success.png)
- [X-Ray trace map](docs/assets/showcase/08-xray-trace-map.png)
- [CloudWatch alarms](docs/assets/showcase/09-cloudwatch-alarms.png)

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

## Implementation Roadmap

The detailed implementation history and planned development direction are
maintained in:

- [Infrastructure Implementation Roadmap](docs/implementation-roadmap.md)

The platform foundations, application workflows, observability baseline,
remote Terraform operations, and separate provisioning and deployment
automation lanes are complete.

The next planned direction focuses on account lifecycle and Cognito
account-management behavior.

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
- Deployment automation is implemented for provisioning, frontend assets, and
  Lambda code updates in `dev`

---

## Documentation

Project documentation is split by purpose:

- [implementation-roadmap.md](docs/implementation-roadmap.md): chronological
  implementation history, completed milestones, and planned development work.
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
