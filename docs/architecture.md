# Architecture Overview

The AWS Serverless Events Platform is a fully managed, cloud-native web application built entirely on AWS serverless services.

## Edge Layer (Global Entry Point)

User traffic enters the system through:

- Amazon CloudFront for global content delivery
- AWS WAF for edge-level protection
- AWS Shield (standard protection)

CloudFront serves static frontend assets from:

- Amazon S3

WAF applies:

- AWS Managed Rule Set
- Rate limiting
- IP filtering (if required)

## Authentication Layer

User authentication is handled by:

- Amazon Cognito

Cognito issues JWT tokens that are validated directly by:

- Amazon API Gateway (JWT Authorizer)

No authentication logic exists inside Lambda functions.

## API Layer

API Gateway (HTTP API) routes requests to individual:

- AWS Lambda functions

Each endpoint is implemented as an independent Lambda to ensure:

- Isolation
- Scalability
- Clear ownership
- Fine-grained IAM control

## Asynchronous Processing Layer

The RSVP workflow uses:

- Amazon Simple Queue Service

Flow:

API Lambda
-> SQS queue
-> Worker Lambda
-> Data persistence

This ensures:

- Back-pressure handling
- Fault tolerance
- Retry logic
- Decoupling of API latency from persistence

## Data Layer

Data is stored in:

- Amazon DynamoDB

Using single-table design with:

- Event metadata
- RSVP items
- GSI for user-based queries

DynamoDB runs in on-demand mode for cost efficiency.

## Event-Driven Extensions

Domain events are published to:

- Amazon EventBridge

Notifications are delivered via:

- Amazon Simple Notification Service

This supports decoupled future integrations.

## Observability

System monitoring includes:

- Amazon CloudWatch for logs and metrics
- AWS X-Ray for request tracing
