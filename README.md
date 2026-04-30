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

- Frontend Deployment Integration
  - define the production deployment path for the built React/Vite frontend
  - keep CloudFront as the only browser-facing entry point
  - wire artifact upload and cache invalidation without changing the `/app` and `/events` route contract

### Completed milestones

- Platform foundations
  - AWS account setup and security baseline
  - repository structure and modular Terraform design
  - API domain contract defined
  - architecture decision validation
- Environment and shared infrastructure
  - `infrastructure/envs/dev` environment foundation
  - `dynamodb_data_layer` module (events + RSVPs tables)
  - `infrastructure/envs/dev` wiring for the DynamoDB data layer
  - `sqs` module (standard queues + optional dedicated DLQs)
  - `infrastructure/envs/dev` wiring for the SQS messaging baseline
  - `iam` module (Lambda execution roles + workload-specific policies)
  - `infrastructure/envs/dev` wiring for the Lambda execution IAM baseline
  - `lambda` module (ZIP-packaged Lambda deployment baseline)
  - `cognito` module (managed identity baseline)
  - `infrastructure/envs/dev` wiring for the Cognito identity baseline
  - `api_gateway` module baseline for routed HTTP API delivery
  - `api_gateway` module hardening:
    - stricter module input validation
    - optional CORS support
    - optional stage access logging
    - default stage throttling
    - per-route throttling overrides
    - `examples/basic_usage`
    - module `README.md`
    - Terraform validation CI coverage for the module and example
  - `s3_frontend_bucket` module baseline for private frontend-origin storage
    - private S3 origin bucket baseline
    - block-all-public-access baseline
    - bucket ownership controls
    - SSE-S3 encryption
    - configurable versioning and force-destroy behavior
    - `examples/basic_usage`
    - module `README.md`
    - Terraform validation CI coverage for the module and example
  - `infrastructure/envs/dev` wiring for the private frontend origin bucket
    - private S3 bucket created in AWS
    - bucket-level public access blocking validated
    - SSE-S3 encryption validated
    - versioning intentionally left suspended in `dev`
    - placeholder `index.html` upload validated
    - direct public object access denied
  - `waf` module baseline for CloudFront edge protection
    - CloudFront-scoped WAFv2 Web ACL baseline
    - fixed AWS managed-rule baseline
    - simple IP-based rate limiting
    - visibility configuration enabled by default
    - `examples/basic_usage`
    - module `README.md`
    - Terraform validation CI coverage for the module and example
  - `infrastructure/envs/dev` optional wiring for the WAF edge protection baseline
    - CloudFront-scoped Web ACL created in AWS
    - Web ACL managed through the required `us-east-1` provider path
    - managed rules validated
    - rate-limit rule validated
    - visibility configuration and tags validated
    - disabled by default in `dev` for cost control until the frontend is actively used
  - `cloudfront` module baseline for edge distribution
    - CloudFront distribution baseline
    - S3 Origin Access Control for private frontend-origin access
    - CloudFront Function for targeted SPA navigation rewrites
    - default static asset behavior backed by S3
    - ordered frontend SPA behaviors for `/app` and `/app/*`
    - ordered backend API behaviors for `/events` and `/events/*`
    - HTTPS redirect behavior
    - managed static caching and API no-cache policies
    - optional WAF Web ACL association input
    - `examples/basic_usage`
    - module `README.md`
    - Terraform validation CI coverage for the module and example
  - `infrastructure/envs/dev` wiring for the CloudFront edge distribution baseline
    - CloudFront distribution created in AWS
    - private S3 frontend bucket attached through Origin Access Control
    - caller-owned S3 bucket policy scoped to the CloudFront distribution ARN
    - frontend SPA route namespace `/app` and `/app/*` routed to S3
    - targeted CloudFront Function rewrite for eligible browser HTML navigations
    - API Gateway origin attached with the existing `/events` route shape
    - optional WAF Web ACL association supported for the distribution
    - HTTPS redirect validated
    - static placeholder delivery through CloudFront validated
    - `/app` SPA deep-link routing through CloudFront validated
    - missing static assets under `/app/*` confirmed not to rewrite to the SPA entrypoint
    - `/events` API routing through CloudFront validated
    - direct S3 public object access remains denied
    - clean post-apply Terraform plan validated
  - `infrastructure/envs/dev` wiring for the routed backend baseline
- Core synchronous Lambda rollout
  - `create-event`
    - implementation
    - `envs/dev` wiring
    - routed AWS validation and deployment evidence
    - JWT-protected `POST /events` route validated in AWS
  - `list-events`
    - implementation
    - `envs/dev` wiring
    - routed AWS validation and deployment evidence
    - now locked as the public broad-list workload
    - public `GET /events` route validated in AWS
  - `list-my-events`
    - implementation
    - `envs/dev` wiring
    - routed AWS validation and deployment evidence
    - dedicated creator-scoped authenticated listing workload
    - JWT-protected `GET /events/mine` route validated in AWS
  - `get-event`
    - implementation
    - `envs/dev` wiring
    - routed AWS validation and deployment evidence
    - public `GET /events/{event_id}` route validated in AWS
  - `update-event`
    - implementation
    - `envs/dev` wiring
    - routed AWS validation and deployment evidence
    - conditional writes, partial updates, and GSI consistency handling
    - JWT-protected `PATCH /events/{event_id}` route validated in AWS
  - `cancel-event`
    - implementation
    - `envs/dev` wiring
    - routed AWS validation and deployment evidence
    - soft-delete lifecycle transition
    - JWT-protected `POST /events/{event_id}/cancel` route validated in AWS
  - `rsvp`
    - implementation
    - `envs/dev` wiring
    - routed AWS validation and deployment evidence
    - transactional RSVP upsert and helper-counter maintenance
    - mixed-mode `POST /events/{event_id}/rsvp` route validated in AWS
  - `get-event-rsvps`
    - implementation
    - `envs/dev` wiring
    - routed AWS validation and deployment evidence
    - creator/admin RSVP read path with pagination
    - JWT-protected `GET /events/{event_id}/rsvps` route validated in AWS
  - `rsvp-authorizer`
    - implementation
    - `envs/dev` wiring
    - AWS validation and deployment evidence
    - mixed anonymous/authenticated caller projection for routed RSVP
- Frontend foundation and product functionality
  - React + Vite + TypeScript app under `frontend/`
  - React Router `BrowserRouter` with `/app` basename
  - Amplify Auth modular Cognito configuration
  - Cognito token storage explicitly configured to `sessionStorage`
  - build-time `VITE_*` public frontend configuration
  - fetch-based API client using same-origin relative `/events` paths
  - public event list page using `GET /events`
  - public event detail page using `GET /events/{event_id}`
  - anonymous RSVP token helper using non-auth `localStorage`
  - mixed-mode RSVP panel using `POST /events/{event_id}/rsvp`
  - authenticated create-event page using `POST /events`
  - authenticated edit-event page using `PATCH /events/{event_id}`
  - authenticated cancel workflow using `POST /events/{event_id}/cancel`
  - authenticated my-events page using `GET /events/mine`
  - creator/admin RSVP list page using `GET /events/{event_id}/rsvps`
  - register, confirm registration, login, and logout flow
  - reusable loading, status, success, and error message components
  - event visibility labels for public, protected, and admin-only events
  - client-side search, sort, event-state, visibility, and RSVP availability controls
    for already loaded event lists
  - light plain-CSS visual polish for layout, forms, buttons, messages, and cards
  - local typecheck/build validation completed
  - manual CloudFront runtime validation completed in the frontend foundation phase
  - no frontend deployment automation added yet
- Validation and developer workflow
  - external Lambda artifact packaging workflow via `scripts/package_lambda.py`
  - Python handler validation for implemented Lambda handlers
  - local pytest bootstrap aligned with CI import-path behavior
  - local `terraform plan` validation for the wired dev environment
  - repository-wide `terraform-docs` configuration
  - Terraform validation CI workflow for DynamoDB module/example, SQS module/example, IAM module/example, Lambda module/example, Cognito module/example, API Gateway module/example, S3 frontend bucket module/example, WAF module/example, CloudFront module/example, and the dev root

### Next milestones

- EventBridge + SNS integration
- `notification-worker`
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

12. After a successful durable write, domain events such as event creation or RSVP confirmation are published to **Amazon EventBridge**.
13. EventBridge routes these events to **Amazon SNS**, enabling notifications and future integrations.
14. **Amazon SQS** remains part of the platform for asynchronous side effects and decoupled follow-up processing such as:
- notification buffering
- enrichment tasks
- reconciliation or repair jobs
- batch imports
- scheduled backfills
- retryable downstream integrations

### Observability

15. Logs and metrics are collected in **Amazon CloudWatch**.
16. Distributed tracing is enabled with **AWS X-Ray** to analyze request performance and dependencies.

This design preserves immediate correctness for core business writes while still enabling scalable asynchronous processing where it adds real value.

---

## Key Architecture Decisions

**Fully Serverless Design**

Avoids infrastructure management and enables automatic scaling.

**Synchronous Core, Async Extensions**

Core RSVP business writes are intentionally kept synchronous so the system can preserve immediate business-result semantics required by the current API contract.

Asynchronous processing is reserved for durable post-commit work, starting with notification dispatch through SQS and expanding later only when additional background workloads are concretely justified.

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
|   |       |-- locals.tf
|   |       |-- main.tf
|   |       |-- outputs.tf
|   |       |-- providers.tf
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
   - dedicated DLQ wiring ✅

4. IAM roles and policies for workloads ✅
   - least-privilege execution roles ✅
   - workload-specific access profiles ✅
   - DynamoDB and SQS policy wiring ✅

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
16. Frontend Deployment Integration
   - local/manual frontend deployment path
   - read required public frontend values from Terraform outputs
   - build the React/Vite frontend with public `VITE_*` values only
   - sync `frontend/dist/` to the private S3 frontend bucket
   - invalidate CloudFront after frontend artifact upload
   - keep CloudFront as the only browser-facing entry point
   - no backend, Lambda, API Gateway, or routing behavior changes

17. Frontend UX + Performance Hardening
   - responsive design pass
   - reusable layout primitives
   - improved visual system
   - accessibility improvements
   - route-level lazy loading
   - pagination UX improvements
   - list rendering optimization
   - bundle/build optimization

18. EventBridge and SNS integration
   - publish domain events only after durable business writes succeed
   - introduce notification fanout without changing synchronous API outcomes

19. `notification-worker`
   - consume asynchronous notification work
   - keep user-facing API responses independent from notification delivery

20. CloudWatch observability and X-Ray tracing
   - add production-oriented logs, metrics, tracing, and validation evidence

21. Remote Terraform backend and GitHub OIDC
   - introduce remote Terraform state
   - add GitHub Actions AWS authentication through OIDC
   - keep this separate from application deployment workflows

22. CI validation workflow hardening
   - keep CI read-only and validation-focused
   - add frontend validation to CI:
     - `npm ci`
     - `npm run typecheck`
     - `npm run build`
   - keep Terraform validation detached from real AWS state
   - do not deploy from CI validation jobs

23. CI/CD deployment workflows
   - add separate provisioning and deployment workflows after OIDC exists
   - keep provisioning responsible for Terraform infrastructure changes
   - keep deployment responsible for application artifacts
   - add frontend deployment workflow for S3 sync and CloudFront invalidation
   - keep Lambda deployment Terraform-managed initially

24. Optional Lambda code deployment separation
   - prepare for a future model where Terraform creates Lambda shell/config
   - move Lambda ZIP artifact publishing to deployment automation
   - update Lambda code with `aws lambda update-function-code`
   - keep IAM, environment variables, log groups, and API wiring in Terraform
   - add versions/aliases only after the basic split is validated


The repository now also includes Terraform validation coverage for the currently
implemented modules, examples, and `envs/dev` root, plus focused Python
validation for the implemented Lambda handlers and shared auth flow.

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
