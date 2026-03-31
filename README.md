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

### Current phase

- Local-first Terraform environment foundation completed
- **DynamoDB business data layer implemented**
- **`infrastructure/envs/dev` now wires the DynamoDB data layer**
- **`infrastructure/envs/dev` now wires the SQS messaging baseline**
- **`infrastructure/envs/dev` now wires the Lambda execution IAM baseline**
- **`lambda` module implemented for ZIP-packaged Lambda deployment and explicit CloudWatch log group ownership**
- **first real Lambda workload implemented: `create-event`**
- **validation workflow now covers DynamoDB module/example, SQS module/example, IAM module/example, Lambda module/example, the dev root, and the first real Lambda handler tests**
- **`infrastructure/envs/dev` now wires the first real Lambda workload**
- Next step: implement the next Lambda workloads, then wire API Gateway and Cognito

### Completed

- AWS account setup and security baseline
- Repository structure and modular Terraform design
- API domain contract defined
- Architecture decision validation
- `infrastructure/envs/dev` environment foundation
- `dynamodb_data_layer` module (events + RSVPs tables)
- `infrastructure/envs/dev` wiring for the DynamoDB data layer
- `sqs` module (standard queues + optional dedicated DLQs)
- `infrastructure/envs/dev` wiring for the SQS messaging baseline
- `iam` module (Lambda execution roles + workload-specific policies)
- `infrastructure/envs/dev` wiring for the Lambda execution IAM baseline
- `lambda` module (ZIP-packaged Lambda deployment baseline)
- first real Lambda workload: `create-event`
- external Lambda artifact packaging workflow via `scripts/package_lambda.py`
- `infrastructure/envs/dev` wiring for the first real Lambda workload
- Python handler validation for `create-event`
- local `terraform plan` validation for the wired dev environment
- Repository-wide `terraform-docs` configuration
- Terraform validation CI workflow for DynamoDB module/example, SQS module/example, IAM module/example, Lambda module/example, and the dev root

### In progress

- PR-based incremental platform infrastructure build-out following the implementation roadmap

### Planned

- Remaining Lambda workloads (`list-events`, `rsvp`, later `notification-worker`)
- EventBridge + SNS integration
- API Gateway + Cognito authentication
- Edge delivery layer (S3 + CloudFront + WAF)
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
5. Protected endpoints require authentication via **Amazon Cognito** using JWT authorizers.

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
|   `-- architecture.md
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
6. EventBridge and SNS integration
7. API Gateway and Cognito authentication
8. Frontend S3 hosting, CloudFront distribution, WAF protection
9. CloudWatch observability and X-Ray tracing
10. Remote Terraform backend and GitHub OIDC
11. CI/CD deployment workflow


The repository now also includes a Terraform validation workflow for the currently implemented module, example, and `envs/dev` root, plus focused Python validation for the first real Lambda handler. That workflow improves static validation confidence, while real AWS creation is still verified through local `plan` and `apply` in the dev environment.

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
- `infrastructure/envs/dev/README.md`
- each module also contains its own `README.md` in the module root directory

---

## Future Improvements

- Custom domain and TLS configuration
- Monitoring dashboards and alerting
- Automated frontend deployment
- Multi-environment promotion strategy
- Advanced security hardening
