# Project Setup

This document explains how to set up this repository from a fresh clone and
provision the `dev` environment.

It covers:

- required local tools
- AWS credential setup
- Terraform bootstrap and remote backend setup
- GitHub Actions input sync
- provisioning dry-run/apply workflows
- Lambda packaging and code deployment helpers
- frontend deployment pointer
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

Use this sequence for a `dev` environment and an AWS account where the local
AWS CLI identity can create the bootstrap resources.

### Required Initial Setup

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
12. Deploy the frontend required for the usable platform:
    ```powershell
    gh workflow run frontend-deploy-dry-run.yml --ref main
    gh workflow run frontend-deploy-apply.yml --ref main -f confirm_deploy=deploy-dev
    ```
13. Validate the frontend, deep-link routing, and `/events` API separation using
    the
    [frontend post-deployment checklist](../frontend/README.md#post-deployment-validation).

The provisioning workflow packages the Lambda artifacts required for initial
function creation. A separate Lambda code deployment is therefore not required
during initial setup.

### Ongoing Infrastructure and Application Updates

Use the provisioning workflows for infrastructure changes:

```powershell
gh workflow run provisioning-dry-run.yml --ref main
gh workflow run provisioning-apply.yml --ref main -f confirm_apply=apply-dev
```

Use the Lambda deployment workflows for code-only Lambda updates:

```powershell
gh workflow run lambda-deploy-dry-run.yml --ref main
gh workflow run lambda-deploy-apply.yml --ref main -f confirm_deploy=deploy-lambdas-dev
```

Use the frontend deployment workflows for frontend updates:

```powershell
gh workflow run frontend-deploy-dry-run.yml --ref main
gh workflow run frontend-deploy-apply.yml --ref main -f confirm_deploy=deploy-dev
```

Equivalent local helper and Terraform alternatives are documented in
[Local Operations](#local-operations).

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
The repository has two workflow categories:

- `.github/workflows/ci.yml` runs automatically for repository validation.
- AWS smoke, provisioning, Lambda deployment, and frontend deployment workflows
  are manually triggered with `workflow_dispatch`.

The operational workflows documented below:

- require `refs/heads/main`
- use repository variables rather than a GitHub Environment
- assume the branch-scoped AWS role through OIDC
- generate `infrastructure/envs/dev/backend.tf`
- initialize and validate the remote-backed Terraform root

Complete [GitHub Actions Input Sync](#github-actions-input-sync) before running
these operational workflows.

### AWS OIDC Smoke Workflow

File: `.github/workflows/aws-oidc-smoke.yml`

```powershell
gh workflow run aws-oidc-smoke.yml --ref main
```

Validates OIDC role assumption, S3 backend bucket and prefix access, and
Terraform initialization and validation. It does not plan, apply, package, or
deploy application artifacts.

### Provisioning Workflows

Files:

- `.github/workflows/provisioning-dry-run.yml`
- `.github/workflows/provisioning-apply.yml`

```powershell
gh workflow run provisioning-dry-run.yml --ref main
gh workflow run provisioning-apply.yml --ref main -f confirm_apply=apply-dev
```

Both workflows consume the synced dev Terraform inputs and package Lambda ZIP
artifacts before planning.

- Dry run: runs `terraform plan` without applying.
- Apply: requires `confirm_apply=apply-dev`, saves the plan, and applies that
  exact plan.

Provisioning does not call `aws lambda update-function-code` or deploy frontend
assets.

### Lambda Deployment Workflows

Files:

- `.github/workflows/lambda-deploy-dry-run.yml`
- `.github/workflows/lambda-deploy-apply.yml`

```powershell
gh workflow run lambda-deploy-dry-run.yml --ref main
gh workflow run lambda-deploy-apply.yml --ref main -f confirm_deploy=deploy-lambdas-dev
```

Both workflows validate the `aws_region` and `lambda_function_names` Terraform
outputs and delegate packaging and deployment behavior to
`scripts/deploy_lambdas.py`.

- Dry run: previews workload-to-function code updates without AWS mutation.
- Apply: requires `confirm_deploy=deploy-lambdas-dev` and updates existing
  function code with `aws lambda update-function-code --no-publish`.

Neither workflow runs Terraform plan/apply, deploys frontend assets, publishes
Lambda versions, manages aliases, or uses CodeDeploy.

### Frontend Deployment Workflows

Files:

- `.github/workflows/frontend-deploy-dry-run.yml`
- `.github/workflows/frontend-deploy-apply.yml`

```powershell
gh workflow run frontend-deploy-dry-run.yml --ref main
gh workflow run frontend-deploy-apply.yml --ref main -f confirm_deploy=deploy-dev
```

Both workflows validate the required frontend Terraform outputs and delegate
build and deployment behavior to `scripts/deploy_frontend.py`.

- Dry run: validates and builds the frontend, then previews the S3 sync.
- Apply: requires `confirm_deploy=deploy-dev`, uploads the assets, and creates a
  CloudFront invalidation.

Neither workflow provisions infrastructure, packages Lambda artifacts, or
deploys Lambda code. Detailed frontend workflow behavior is documented in
[frontend/README.md](../frontend/README.md#github-actions-workflows).

---

## Local Operations

### Lambda Packaging

Build the complete Lambda artifact set from the repository root:

```powershell
python scripts/package_lambdas.py
```

Artifacts are written to `artifacts/lambda/<function-key>.zip`. Packaging
behavior, workload-specific rules, and the RSVP authorizer vendor build are
documented in [lambdas/README.md](../lambdas/README.md).

### Lambda Code Deployment Helper

`scripts/deploy_lambdas.py` packages the deployed workloads, reads the
remote-backed Terraform outputs, validates the workload-to-function mapping,
and previews or applies code-only Lambda updates.

It requires these Terraform outputs:

- `aws_region`
- `lambda_function_names`

Preview a deployment from the repository root:

```powershell
python scripts/deploy_lambdas.py --dry-run
```

Apply the code update:

```powershell
python scripts/deploy_lambdas.py --apply
```

Dry-run prints the planned `aws lambda update-function-code` commands without
AWS mutation. Apply mode updates existing function code after running the same
packaging and validation path.

The helper does not run `terraform plan`, run `terraform apply`, publish Lambda
versions, manage aliases, use CodeDeploy, or deploy frontend assets.

Use the corresponding manual workflows documented in
[Lambda Deployment Workflows](#lambda-deployment-workflows) for GitHub Actions.

### Frontend Operations

Run local validation from `frontend/`:

```powershell
npm ci
npm run typecheck
npm run build
npm run test
npm run test:e2e
```

Run frontend deployment previews or updates from the repository root:

```powershell
python scripts/deploy_frontend.py --dry-run
python scripts/deploy_frontend.py --apply
```

Detailed frontend setup, runtime rules, helper behavior, and post-deployment
checks are documented in [frontend/README.md](../frontend/README.md).

Use the corresponding manual workflows documented in
[Frontend Deployment Workflows](#frontend-deployment-workflows) for GitHub
Actions.

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

Tool usage summary:

- Python: Lambda runtime alignment, helper scripts, and handler tests
- Docker: Lambda-compatible RSVP authorizer vendor rebuild
- Terraform: bootstrap, provisioning, validation, and outputs
- `tflint`: Terraform linting
- `terraform-docs`: generated Terraform README sections
- AWS CLI: local frontend artifact deployment and Lambda code updates
- GitHub CLI: repository input sync and manual workflow runs
- Node.js and npm: frontend validation and builds under `frontend/`

## Python

- use Python `3.13` for deployed Lambda runtime compatibility
- local helper scripts in `scripts/` are also Python-based where practical
- local Python virtual environments such as `.venv` are recommended for tests,
  helper scripts, and local dependency installs

Python-based local workflows include Lambda packaging, RSVP authorizer vendor
builds, repository helper scripts, and focused handler tests.

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

Docker is currently required for the mixed-mode RSVP authorizer packaging flow:

- the authorizer depends on native libraries such as `cryptography` and `cffi`
- local importability is not the same as Lambda-runtime compatibility
- the repository now uses a Docker-based rebuild step to generate a
  Lambda-compatible vendor tree for:
  - `lambdas/rsvp_authorizer/vendor/`

Docker is not currently required for ordinary Lambda packaging or Terraform
validation. It is specifically required for the RSVP authorizer vendor rebuild
flow.

## Terraform

Terraform is the source of truth for infrastructure in this repository. Local
Terraform usage includes:

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

The AWS CLI is required for local deployment helpers. It must be configured for
the same AWS account and dev permissions used by the platform.

The frontend helper uses AWS CLI commands for:

- previewing frontend artifact changes in dry-run mode
- syncing `frontend/dist/` to the private frontend S3 bucket in apply mode
- creating a CloudFront cache invalidation after a real frontend upload

The Lambda deployment helper uses AWS CLI commands for:

- updating existing Lambda function code with `aws lambda update-function-code`
  only when run with `--apply`
