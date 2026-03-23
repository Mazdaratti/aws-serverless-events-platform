# AWS Serverless Events Platform

A production-style, fully AWS-native serverless web application for managing events and RSVP workflows.

The system demonstrates modern cloud architecture patterns including event-driven processing, managed authentication, edge security, and Infrastructure as Code using Terraform.

This project is designed as a **cloud engineering portfolio showcase** and follows real-world engineering practices such as least-privilege IAM, cost-aware design, and incremental infrastructure delivery.

---

## Project Goals

- Build a production-shaped serverless system using managed AWS services
- Demonstrate asynchronous event-driven architecture
- Apply security best practices (edge protection, managed identity, least privilege)
- Implement observability and operational readiness
- Use Terraform for reproducible infrastructure
- Follow clean Git workflow and modular infrastructure design
- Stay within AWS Free Tier and promotional credits

---

## Current Development Status

**Current phase**

- Local-first Terraform environment foundation implemented
- Core serverless data platform under development
- CI/CD and remote Terraform backend planned for a later phase

**Completed**

- AWS account setup
- Repository structure initialization
- Architecture planning
- API domain contract defined
- `infrastructure/envs/dev` environment foundation
- repository-wide `terraform-docs` configuration

**In progress**

- Core data and messaging components

**Planned**

- Lambda compute layer
- API and authentication layer
- Edge delivery layer
- Observability and deployment automation

---

## Target Architecture

The platform uses native AWS serverless services:

- Amazon CloudFront
- AWS WAF
- Amazon S3
- Amazon API Gateway (HTTP API)
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

### Asynchronous RSVP Processing

8. RSVP submissions are handled by an **enqueue Lambda**, which places messages into **Amazon SQS**.
9. A separate **worker Lambda** processes queue messages independently from user requests.
10. Processed RSVP data is written to **DynamoDB**.

### Event-Driven Extensions

11. Domain events such as event creation or RSVP confirmation are published to **Amazon EventBridge**.
12. EventBridge routes these events to **Amazon SNS**, enabling notifications and future integrations.

### Observability

13. Logs and metrics are collected in **Amazon CloudWatch**.
14. Distributed tracing is enabled with **AWS X-Ray** to analyze request performance and dependencies.

This asynchronous design improves scalability, resilience, and failure isolation.

---

## Key Architecture Decisions

**Fully Serverless Design**

Avoids infrastructure management and enables automatic scaling.

**Asynchronous Processing Pattern**

SQS and worker Lambdas decouple API responsiveness from background processing.

**Managed Authentication**

Amazon Cognito replaces custom authentication logic, improving security and reducing operational overhead.

**No VPC Architecture**

Simplifies networking and keeps costs low while still supporting production-grade patterns.

**Local Terraform State First**

Infrastructure is initially developed using local state for rapid iteration.  
Remote backend and deployment automation will be introduced later.

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
|       |-- dynamodb/
|       |-- eventbridge/
|       |-- iam/
|       |-- lambda/
|       |-- sqs/
|       `-- waf/
|
|-- lambdas/
|   |-- create_event/
|   |   `-- .gitkeep
|   |-- list_events/
|   |   `-- .gitkeep
|   |-- rsvp_enqueue/
|   |   `-- .gitkeep
|   |-- rsvp_worker/
|   |   `-- .gitkeep
|   `-- shared/
|       `-- .gitkeep
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

1. Terraform environment foundation (local state)
2. DynamoDB data tables
3. SQS queues and dead-letter queues
4. IAM roles and policies for workloads
5. Lambda compute layer
6. EventBridge and SNS integration
7. API Gateway and Cognito authentication
8. Frontend S3 hosting, CloudFront distribution, WAF protection
9. CloudWatch observability and X-Ray tracing
10. Remote Terraform backend and GitHub OIDC
11. CI/CD deployment workflow

---

## Security Principles

- Least-privilege IAM access
- Edge protection using AWS WAF
- Private S3 origin behind CloudFront
- Managed identity via Amazon Cognito
- Failure isolation using SQS dead-letter queues

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

---

## Future Improvements

- Custom domain and TLS configuration
- Monitoring dashboards and alerting
- Automated frontend deployment
- Multi-environment promotion strategy
- Advanced security hardening
