# Project Setup

This document explains how to set up this repository from a fresh clone and
provision the `dev` environment.

It covers:

- required local tools
- AWS credential setup
- Terraform bootstrap
- remote state initialization
- `dev` environment provisioning
- Lambda code deployment
- frontend deployment
- validation commands

---

## Current Setup Model

`infrastructure/bootstrap/dev` creates the remote state bucket, generated
backend config, and GitHub OIDC role. The `infrastructure/envs/dev` root uses
the generated S3 backend.

GitHub repository variables and secrets are synced from bootstrap outputs and
local dev Terraform inputs for the manual AWS OIDC smoke workflow, provisioning
workflows, Lambda deployment workflows, and frontend deployment workflows.

Terraform provisioning, Lambda code deployment, and frontend deployment are
separate operational lanes.

---

## Setup Sequence

Use this order when setting up the project from a fresh clone. The sequence
assumes a `dev` environment and an AWS account where the local AWS CLI identity
is allowed to create the bootstrap resources.

1. Clone the repository.
2. Install the required local tools listed in
   [Current Tooling Baseline](#current-tooling-baseline).
3. Configure AWS CLI credentials for the target AWS account and verify them:
   ```powershell
   aws sts get-caller-identity
   ```
4. Copy and edit the bootstrap variables:
   - `infrastructure/bootstrap/dev/terraform.tfvars.example`
   - `infrastructure/bootstrap/dev/terraform.tfvars`
5. Initialize, validate, and apply the bootstrap root locally:
   ```powershell
   terraform -chdir=infrastructure/bootstrap/dev init
   terraform -chdir=infrastructure/bootstrap/dev validate -no-color
   terraform -chdir=infrastructure/bootstrap/dev apply
   ```
6. Confirm the generated backend config exists and is ignored by Git:
   ```powershell
   Get-Content infrastructure/envs/dev/backend.tf
   git status --short --ignored -- infrastructure/envs/dev/backend.tf
   ```
7. Copy and edit the `dev` environment variables:
   - `infrastructure/envs/dev/terraform.tfvars.example`
   - `infrastructure/envs/dev/terraform.tfvars`
8. Sync GitHub repository variables and secrets for GitHub Actions:
   ```powershell
   python scripts/sync_github_actions_vars.py --dry-run
   python scripts/sync_github_actions_vars.py
   gh variable list
   gh secret list
   ```
9. Run the manual AWS OIDC smoke workflow from `main`:
   ```powershell
   gh workflow run aws-oidc-smoke.yml --ref main
   ```
10. Run the manual provisioning dry-run workflow from `main`:
    ```powershell
    gh workflow run provisioning-dry-run.yml --ref main
    ```
11. Run the manual provisioning apply workflow from `main` to create or update
    the `dev` infrastructure:
    ```powershell
    gh workflow run provisioning-apply.yml --ref main -f confirm_apply=apply-dev
    ```
12. Run the manual Lambda deployment dry-run workflow from `main`:
    ```powershell
    gh workflow run lambda-deploy-dry-run.yml --ref main
    ```
13. Deploy the frontend with one of the implemented frontend paths:
    ```powershell
    python scripts/deploy_frontend.py --dry-run
    python scripts/deploy_frontend.py --apply
    gh workflow run frontend-deploy-dry-run.yml --ref main
    gh workflow run frontend-deploy-apply.yml --ref main -f confirm_deploy=deploy-dev
    ```
14. Validate the CloudFront frontend and `/events` API routes.

    Check the app through the CloudFront domain printed by the deployment
    helper or available from Terraform outputs:
    - `/app`
    - `/app/events`
    - `/app/my-events`
    - `/events`

    Frontend routes under `/app` should return the SPA. API routes under
    `/events` should return API responses, not frontend HTML.

---

## GitHub Actions Input Sync

Local developers can continue to use the untracked dev tfvars file:

- `infrastructure/envs/dev/terraform.tfvars`

GitHub Actions cannot read that local file. The unified sync helper publishes
both bootstrap-derived values and supported dev Terraform inputs into GitHub:

```powershell
python scripts/sync_github_actions_vars.py --dry-run
python scripts/sync_github_actions_vars.py
```

Dry-run mode prints the planned GitHub variable and secret names without
updating GitHub. The helper uses Terraform only to read bootstrap outputs. It
does not call AWS directly and does not run Terraform plan/apply.

The helper sets these bootstrap-derived repository variables:

- `AWS_ROLE_TO_ASSUME`
- `AWS_REGION`
- `TF_BACKEND_BUCKET`
- `TF_BACKEND_KEY`

The helper sets these dev Terraform repository variables:

- `DEV_PROJECT_NAME`
- `DEV_ENVIRONMENT`
- `DEV_DYNAMODB_POINT_IN_TIME_RECOVERY_ENABLED`
- `DEV_ENABLE_WAF`

The helper sets these dev Terraform repository secrets:

- `DEV_SES_SENDER_EMAIL`
- `DEV_SNS_ADMIN_EMAIL_SUBSCRIPTIONS_JSON`

GitHub workflows consume the synced values through repository variables,
repository secrets, and `TF_VAR_*` environment variables. The local
`terraform.tfvars` file remains operator-owned and must not be committed.

---

## GitHub Actions Workflows

GitHub Actions uses the OIDC role created by `infrastructure/bootstrap/dev`.
The current OIDC trust is branch-scoped to `main`, so these workflows use
repository variables and do not use a GitHub Environment.

Before running GitHub Actions workflows, complete the repository variable and
secret sync described in [GitHub Actions Input Sync](#github-actions-input-sync).

### AWS OIDC Smoke Workflow

Workflow file:

- `.github/workflows/aws-oidc-smoke.yml`

Run it from `main` with:

```powershell
gh workflow run aws-oidc-smoke.yml --ref main
```

This workflow validates:

- GitHub Actions can request an OIDC token
- AWS accepts the token for the branch-scoped role
- the assumed role can access the configured S3 remote state bucket and backend
  key prefix
- Terraform can initialize against the generated S3 backend settings
- Terraform can validate `infrastructure/envs/dev`

It does not run `terraform plan`, run `terraform apply`, package Lambda
artifacts, deploy Lambda code, or deploy frontend assets.

### Provisioning Dry Run Workflow

Workflow file:

- `.github/workflows/provisioning-dry-run.yml`

Run it from `main` with:

```powershell
gh workflow run provisioning-dry-run.yml --ref main
```

This validation-only provisioning dry run uses synced GitHub variables and
secrets, generates the dev backend configuration, packages Lambda ZIP artifacts,
and runs:

- `terraform init`
- `terraform validate`
- `terraform plan`

It does not apply infrastructure, deploy Lambda code, or deploy frontend assets.

### Provisioning Apply Workflow

Workflow file:

- `.github/workflows/provisioning-apply.yml`

Run it from `main` with the required confirmation input:

```powershell
gh workflow run provisioning-apply.yml --ref main -f confirm_apply=apply-dev
```

This workflow is the GitHub Actions path for initial `dev` environment
provisioning after bootstrap and input sync are complete, and for later
infrastructure changes. It uses synced GitHub variables and secrets, generates
the dev backend configuration, packages Lambda ZIP artifacts, and runs:

- `terraform init`
- `terraform validate`
- `terraform plan -out=tfplan`
- `terraform apply tfplan`

It requires explicit confirmation and applies only the saved Terraform plan. It
does not deploy Lambda code through `aws lambda update-function-code` or deploy
frontend assets.

### Lambda Deployment Dry Run Workflow

Workflow file:

- `.github/workflows/lambda-deploy-dry-run.yml`

Run it from `main` with:

```powershell
gh workflow run lambda-deploy-dry-run.yml --ref main
```

This workflow validates the Lambda code deployment lane. It uses GitHub OIDC,
generates the dev backend configuration from repository variables, initializes
and validates the remote Terraform backend, checks the required Lambda
deployment outputs, and then runs:

```powershell
python scripts/deploy_lambdas.py --dry-run
```

It does not run `terraform plan`, run `terraform apply`, call
`aws lambda update-function-code`, or deploy frontend assets.

### Frontend Deployment Workflows

Workflow files:

- `.github/workflows/frontend-deploy-dry-run.yml`
- `.github/workflows/frontend-deploy-apply.yml`

Run the dry-run workflow from `main` with:

```powershell
gh workflow run frontend-deploy-dry-run.yml --ref main
```

Run the apply workflow from `main` with the required confirmation input:

```powershell
gh workflow run frontend-deploy-apply.yml --ref main -f confirm_deploy=deploy-dev
```

These workflows use GitHub OIDC, generate the dev backend configuration from
repository variables, initialize the remote Terraform backend, check required
frontend deployment outputs, and then run the frontend deployment helper.

The dry-run workflow builds and previews deployment only. The apply workflow
uploads frontend assets and creates the CloudFront invalidation. Neither
workflow runs Terraform provisioning, packages Lambda artifacts, or deploys
Lambda code.

---

## Local Helper Commands

### Lambda Packaging

Provisioning workflows and Lambda code deployment workflows use the same
packaging path:

```powershell
python scripts/package_lambdas.py
```

The helper packages all deployed Lambda workloads into:

- `artifacts/lambda/<function-key>.zip`

It also rebuilds the Lambda-compatible RSVP authorizer vendor tree by default.

### Lambda Code Deployment Helper

The local Lambda code deployment helper is:

- `scripts/deploy_lambdas.py`

Before using the helper, make sure the dev Terraform state is current and
includes the Lambda deployment outputs:

- `aws_region`
- `lambda_function_names`

Run a safe dry-run first from the repository root:

```powershell
python scripts/deploy_lambdas.py --dry-run
```

Dry-run mode packages all deployed Lambda workloads, reads
`terraform output -json`, validates the workload-to-function mapping, validates
expected ZIP artifacts, and prints the planned
`aws lambda update-function-code` commands.

For a real Lambda code deployment, run:

```powershell
python scripts/deploy_lambdas.py --apply
```

Apply mode uses the same packaging and validation path, then updates existing
Lambda function code with `aws lambda update-function-code`.

The helper does not run `terraform plan`, run `terraform apply`, publish Lambda
versions, manage aliases, use CodeDeploy, or deploy frontend assets.

### Frontend Operations

Detailed frontend setup, validation, runtime rules, deployment helper behavior,
and post-deployment checks are documented in:

- `frontend/README.md`

Common local validation commands from `frontend/`:

```powershell
npm ci
npm run typecheck
npm run build
npm run test
npm run test:e2e
```

Common frontend deployment commands from the repository root:

```powershell
python scripts/deploy_frontend.py --dry-run
python scripts/deploy_frontend.py --apply
```

### Local Terraform Provisioning Alternative

Local Terraform provisioning remains available for operator-driven validation
or recovery, but it is an alternative to the GitHub Actions provisioning apply
workflow, not an additional required setup step.

From the repository root:

```powershell
terraform -chdir=infrastructure/envs/dev init
terraform -chdir=infrastructure/envs/dev validate -no-color
terraform -chdir=infrastructure/envs/dev plan -out=tfplan
terraform -chdir=infrastructure/envs/dev apply tfplan
terraform -chdir=infrastructure/envs/dev plan
```

The final plan should report no changes after a successful apply.

---

## Deployment Boundaries

### Terraform Provisioning vs Lambda Code Deployment

Lambda infrastructure ownership is separate from Lambda code deployment, while
Lambda artifact generation remains available to both automation lanes.

- Terraform continues to own Lambda infrastructure, configuration, and service
  wiring.
- Terraform provisioning builds Lambda ZIP artifacts before Terraform
  plan/apply so Terraform can create Lambda functions when needed.
- After Lambda functions exist, Terraform ignores Lambda package-field drift
  while continuing to detect infrastructure and configuration drift.
- Lambda code deployment automation builds Lambda ZIP artifacts, maps workloads
  to existing function names from Terraform outputs, and updates code through
  `aws lambda update-function-code`.
- Lambda code deployment workflows may read Terraform outputs, but they must
  not run `terraform apply`.

Config drift such as environment variables, timeout, memory, tracing, IAM,
event source mappings, and API Gateway wiring must remain visible to Terraform.

### Frontend Deployment Boundary

Frontend deployment uploads static assets to S3 and creates a CloudFront
invalidation in apply mode.

Frontend deployment does not:

- run Terraform provisioning
- package Lambda artifacts
- deploy Lambda code

Detailed frontend operations are documented in:

- `frontend/README.md`

---

## Current Tooling Baseline

The project workflow expects these tools to be available:

- Python
- Docker
- Terraform
- `tflint`
- `terraform-docs`
- AWS CLI
- GitHub CLI
- Node.js
- npm

These tools support the setup and validation workflow:

- Python is used for Lambda source code, tests, and helper scripts
- Docker is used for Lambda-compatible vendored dependency builds where native
  dependencies are involved
- Terraform is used for infrastructure validation, planning, and deployment
- `tflint` is used for Terraform linting
- `terraform-docs` is used to refresh generated module and environment README sections
- AWS CLI is used by local deployment helpers for frontend S3/CloudFront
  deployment and Lambda code updates
- GitHub CLI is used to sync repository variables and run manual GitHub
  Actions workflows
- Node.js and npm are used for the React/Vite frontend application under
  `frontend/`

## Python

Current project direction:

- use Python `3.13` for deployed Lambda runtime compatibility
- local helper scripts in `scripts/` are also Python-based where practical
- local Python virtual environments such as `.venv` are recommended for tests,
  helper scripts, and local dependency installs

Examples of Python-based local workflow:

- packaging Lambda ZIP artifacts:
  - `scripts/package_lambda.py`
- rebuilding the RSVP authorizer vendor tree:
  - `scripts/build_rsvp_authorizer_vendor.py`
- running focused handler tests

Local test execution now uses the shared pytest bootstrap under:

- `tests/conftest.py`

That bootstrap aligns local import-path behavior with CI so Lambda handlers can
be tested locally using the same `shared/...` import layout expected by the
packaged deployment artifacts.

Install the local Lambda test dependencies into the repository virtual
environment before running handler tests locally:

```powershell
.\.venv\Scripts\python.exe -m pip install pytest boto3
```

`boto3` also installs `botocore`, which the tests use for AWS SDK exception
shapes and mocked client behavior. These dependencies are for local unit tests
and helper scripts; they do not require AWS credentials for mocked handler
tests.

## Docker

Docker is currently required for the mixed-mode RSVP authorizer packaging flow.

Why:

- the authorizer depends on native libraries such as `cryptography` and `cffi`
- local importability is not the same as Lambda-runtime compatibility
- the repository now uses a Docker-based rebuild step to generate a
  Lambda-compatible vendor tree for:
  - `lambdas/rsvp_authorizer/vendor/`

Docker is not currently required for ordinary Lambda packaging or Terraform
validation. It is specifically required for the RSVP authorizer vendor rebuild
flow.

## Terraform

Terraform is the source of truth for infrastructure in this repository.

The local workflow currently uses Terraform for:

- `fmt`
- `init`
- `validate`
- `plan`
- targeted environment/module verification during implementation

## `tflint`

`tflint` is part of the expected Terraform validation workflow for:

- modules
- examples
- `infrastructure/envs/dev`

## `terraform-docs`

`terraform-docs` is part of the expected documentation maintenance workflow
for:

- Terraform modules
- `infrastructure/envs/dev`

It is used to refresh generated input/output/reference sections in README files
after interface changes.

## AWS CLI

The AWS CLI is required for local application artifact deployment workflows.

For the current frontend and Lambda deployment helpers, the AWS CLI must be
able to access the same AWS account and permissions used for the dev
environment.

The frontend helper uses AWS CLI commands for:

- previewing and syncing `frontend/dist/` to the private frontend S3 bucket
- creating a CloudFront cache invalidation after a real frontend upload

The Lambda deployment helper uses AWS CLI commands for:

- updating existing Lambda function code with `aws lambda update-function-code`
  only when run with `--apply`
