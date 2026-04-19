# AWS Serverless Events Platform

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

- Routed API completion and end-to-end AWS validation are the current implementation focus
- Cognito identity infrastructure is now implemented, wired in `envs/dev`, and validated in AWS
- public `GET /events` and JWT-protected `GET /events/mine` are now implemented, wired in `envs/dev`, and validated in AWS
- public `GET /events/{event_id}` is now implemented, wired in `envs/dev`, and validated in AWS
- the mixed-mode RSVP authorizer contract is now implemented and validated in AWS
- the next steps are to:
  - wire the real mixed-mode routed `rsvp` path
  - remove the temporary authorizer probe validation slice after the milestone is fully documented and merged
  - continue shifting the platform from direct Lambda invocation assumptions toward fully routed API behavior
- this milestone already proves:
  - public routed event reads
  - JWT-protected routed event reads
  - correct API Gateway-enforced auth boundaries in AWS
  - the mixed anonymous/authenticated authorizer contract required for the future RSVP route

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
- Core synchronous Lambda rollout
  - `create-event`
    - implementation
    - `envs/dev` wiring
    - AWS validation and deployment evidence
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
    - AWS validation and deployment evidence
    - conditional writes, partial updates, and GSI consistency handling
  - `cancel-event`
    - implementation
    - `envs/dev` wiring
    - AWS validation and deployment evidence
    - soft-delete lifecycle transition
  - `rsvp`
    - implementation
    - `envs/dev` wiring
    - AWS validation and deployment evidence
    - transactional RSVP upsert and helper-counter maintenance
  - `get-event-rsvps`
    - implementation
    - `envs/dev` wiring
    - AWS validation and deployment evidence
    - creator/admin RSVP read path with pagination
- Validation and developer workflow
  - external Lambda artifact packaging workflow via `scripts/package_lambda.py`
  - Python handler validation for implemented Lambda handlers
  - local `terraform plan` validation for the wired dev environment
  - repository-wide `terraform-docs` configuration
  - Terraform validation CI workflow for DynamoDB module/example, SQS module/example, IAM module/example, Lambda module/example, Cognito module/example, and the dev root

### Next milestones

- Edge delivery layer (S3 + CloudFront + WAF)
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

## System Workflow

### Frontend Delivery

1. Users access the application through **Amazon CloudFront**.
2. CloudFront securely serves static frontend assets from a private **Amazon S3** bucket.
3. **AWS WAF** filters malicious traffic at the edge before requests reach the backend.

### API Request Flow

4. The frontend sends API requests to **Amazon API Gateway**.
5. Route protection is enforced at API Gateway using a hybrid authorizer model:
   - native JWT authorizer for ordinary protected routes
   - a dedicated Lambda authorizer for the mixed-mode RSVP route

### Event Management

6. API Gateway invokes a **Lambda function** to create or retrieve event data.
7. Event information is stored in **Amazon DynamoDB**, providing scalable serverless persistence.

### RSVP Processing

8. RSVP submissions are handled as a **synchronous business operation**.
9. The primary RSVP write path is:

`Client -> API Gateway -> Lambda -> DynamoDB transaction`

10. This design preserves the current API contract so the caller immediately knows whether:
- the RSVP was created
- the RSVP was updated
- the event is already at capacity
- access is forbidden
- the event does not exist

### Event-Driven Extensions

11. After a successful durable write, domain events such as event creation or RSVP confirmation are published to **Amazon EventBridge**.
12. EventBridge routes these events to **Amazon SNS**, enabling notifications and future integrations.
13. **Amazon SQS** remains part of the platform for asynchronous side effects and decoupled follow-up processing such as:
- notification buffering
- enrichment tasks
- reconciliation or repair jobs
- batch imports
- scheduled backfills
- retryable downstream integrations

### Observability

14. Logs and metrics are collected in **Amazon CloudWatch**.
15. Distributed tracing is enabled with **AWS X-Ray** to analyze request performance and dependencies.

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

The routed API intentionally uses a hybrid authorizer model so ordinary protected
routes stay simple while the RSVP route can support anonymous and authenticated
callers on one business operation.

**No VPC Architecture**

Simplifies networking and keeps costs low while still supporting production-grade patterns.

**Local Terraform State First**

Infrastructure is initially developed using local state for rapid iteration.  
Remote backend and deployment automation will be introduced later.

**Modular Terraform Design**

Reusable infrastructure logic is implemented in focused Terraform modules, while `infrastructure/envs/dev` stays thin and composition-oriented.

This keeps changes reviewable, reduces refactoring churn, and supports future multi-environment expansion.

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
|   |   `-- .gitkeep
|   `-- src/
|       `-- .gitkeep
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
|       |-- sqs/
|       `-- waf/
|
|-- lambdas/
|   `-- Python Lambda workload source folders and shared placeholder structure
|
|-- scripts/
|   `-- Python helper scripts for packaging and local build workflows
|
|-- tests/
|   `-- Focused automated tests for implemented Lambda handlers and future application code
|
|-- .gitignore
|-- .terraform-docs.yml
|-- LICENSE
`-- README.md
```

Infrastructure is implemented using modular Terraform design with environment-specific composition.

---

## Infrastructure Implementation Roadmap

Planned implementation sequence:

1. Terraform environment foundation (local state) ✅
2. DynamoDB business data layer ✅
3. SQS queues and dead-letter queues ✅
4. IAM roles and policies for workloads ✅
5. Lambda compute layer ✅
6. Core synchronous Lambda workload rollout
   - `create-event` ✅
   - `list-events` ✅
   - `get-event` ✅
   - `update-event` ✅
   - `cancel-event` ✅
   - `rsvp` ✅
   - `get-event-rsvps` ✅
   - note: workload implementations are complete, and routed API rollout is now
     being finished incrementally route by route
7. Cognito authentication baseline (foundation) ✅
   - Cognito User Pool ✅
   - public app client ✅
   - admin group ✅
8. Lambda identity normalization across authorizer modes
   - shared caller normalization helper ✅
   - shared helper test coverage ✅
   - shared packaging support for `shared/...` imports ✅
   - `create-event` normalization adoption ✅
   - `update-event` normalization adoption ✅
   - `cancel-event` normalization adoption ✅
   - `get-event-rsvps` normalization adoption ✅
   - `list-events` public-only cleanup ✅
9. `list-my-events` workload split from `list-events` ✅
10. Mixed-mode RSVP lambda authorizer ✅
11. `rsvp` normalization for mixed-mode authorizer contract
12. API Gateway routed validation and rollout
   - narrow protected `create-event` route slice ✅ (end-to-end validated)
   - incremental protected `update-event` route slice ✅ (end-to-end validated)
   - incremental protected `cancel-event` route slice ✅ (end-to-end validated)
   - incremental protected `get-event-rsvps` route slice ✅ (end-to-end validated)
   - public `list-events` route slice ✅ (end-to-end validated)
   - JWT-protected `list-my-events` route slice ✅ (end-to-end validated)
   - public `get-event` route slice ✅ (end-to-end validated)
   - mixed-mode authorizer probe slice ✅ (end-to-end validated)
   - next routed step: real mixed-mode `rsvp`
13. Frontend S3 hosting, CloudFront distribution, WAF protection
14. EventBridge and SNS integration
15. `notification-worker`
16. CloudWatch observability and X-Ray tracing
17. Remote Terraform backend and GitHub OIDC
18. CI/CD deployment workflow


The repository now also includes a Terraform validation workflow for the currently implemented modules, examples, and `envs/dev` root, plus focused Python validation for the implemented Lambda handlers. That workflow improves static validation confidence, while real AWS creation is still verified through local `plan` and `apply` in the dev environment.

---

## Security Principles

- Least-privilege IAM access
- Edge protection using AWS WAF
- Private S3 origin behind CloudFront
- Managed identity via Amazon Cognito
- Failure isolation using SQS dead-letter queues where asynchronous processing is used

---

## Cost Awareness

The system is designed to operate within:

- AWS promotional credits
- Always-free service limits

No EC2 instances, NAT Gateways, or relational databases are used.

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

The current local backend and infrastructure workflow expects:

- Python
- Docker
- Terraform
- `tflint`

Frontend tooling is not yet a hard project baseline, but Node.js and npm are
expected to be added once frontend implementation becomes an active track.

See:

- `docs/local-setup.md`

---

## Future Improvements

- Custom domain and TLS configuration
- Monitoring dashboards and alerting
- Automated frontend deployment
- Multi-environment promotion strategy
- Advanced security hardening
