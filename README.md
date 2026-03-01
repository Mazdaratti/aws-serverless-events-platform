# AWS Serverless Events Platform

A production-grade, fully AWS-native, serverless web application built using managed AWS services and Infrastructure as Code.

This project demonstrates advanced cloud architecture, event-driven design, security best practices, and cost-aware engineering.

## Architecture

### Core Services

- Amazon CloudFront
- AWS WAF
- Amazon S3
- Amazon API Gateway
- AWS Lambda
- Amazon DynamoDB
- Amazon Cognito
- Amazon Simple Queue Service
- Amazon EventBridge
- Amazon Simple Notification Service
- Amazon CloudWatch
- AWS X-Ray
- AWS Shield

### Key Features

- Fully serverless (no EC2, no containers)
- Edge-level security
- Managed authentication
- Asynchronous processing
- Event-driven extensions
- Infrastructure as Code (Terraform)
- Modular multi-environment structure
- Cost-optimized for AWS Free Tier + credits

## Repository Structure

```text
aws-serverless-events-platform/
|
|-- frontend/
|   |-- src/
|   `-- public/
|
|-- lambdas/
|   |-- create_event/
|   |-- list_events/
|   |-- rsvp_enqueue/
|   |-- rsvp_worker/
|   `-- shared/
|
|-- infrastructure/
|   |-- modules/
|   |   |-- dynamodb/
|   |   |-- lambda/
|   |   |-- api_gateway/
|   |   |-- cognito/
|   |   |-- sqs/
|   |   |-- eventbridge/
|   |   |-- cloudfront/
|   |   |-- waf/
|   |   `-- iam/
|   |
|   `-- envs/
|       `-- dev/
|           |-- main.tf
|           |-- variables.tf
|           |-- outputs.tf
|           |-- backend.tf
|           `-- providers.tf
|
|-- .github/workflows/
|   `-- ci.yml
|
|-- docs/
|   `-- architecture.md
|
`-- README.md
```

## Cost Awareness

Designed to operate within:

- AWS promotional credits ($200)
- Always-free service limits

No VPC, no NAT Gateway, and no RDS.

## Development Status

Bootstrap phase - infrastructure foundation in progress.
