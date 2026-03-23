# Development Environment (`envs/dev`)

This folder contains the Terraform root module for the local-first `dev` environment.

At this stage, the environment is intentionally small. It does not create AWS application resources yet. Instead, it establishes the shared Terraform, provider, naming, tagging, and input baseline that future module wiring will build on.

This environment will later deploy a fully serverless event platform on AWS using API Gateway, Lambda, DynamoDB, SQS, EventBridge, SNS, Cognito, CloudFront, and WAF.

---

## What This Environment Does Right Now

The current `dev` root module is responsible for:

- defining Terraform and AWS provider version constraints
- configuring the AWS provider for the selected region
- establishing shared environment naming and baseline tags
- declaring the required input values for local use

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

Because this foundation step does not create AWS resources yet, the plan is still useful to:

- validate provider authentication
- validate variable wiring
- validate the dependency lock file
- validate the evaluation graph for the environment root

---

## File Overview

- `versions.tf` keeps the Terraform CLI and AWS provider version baseline in one place
- `locals.tf` defines shared naming and tagging values for future module composition
- `variables.tf` declares the required environment inputs and validates that they are not empty
- `providers.tf` configures the AWS provider and applies baseline default tags
- `main.tf` is the future composition entrypoint for reusable module wiring
- `terraform.tfvars.example` shows the required local input shape for this environment

---

## Next Step In This Environment

As reusable modules are implemented under `infrastructure/modules`, this root module will wire them together gradually.

The environment should stay thin:

- reusable AWS resource logic belongs in modules
- `envs/dev` should focus on composition and environment-level identity and placement inputs

---

<!-- BEGIN_TF_DOCS -->
<!-- END_TF_DOCS -->
