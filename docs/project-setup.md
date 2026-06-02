# Project Setup

This document explains how to set up this repository from a fresh clone and
provision the `dev` environment.

It covers:

- required local tools
- AWS credential setup
- Terraform bootstrap
- remote state initialization
- `dev` environment provisioning
- frontend deployment
- validation commands

> Current setup model: `infrastructure/bootstrap/dev` creates the remote state
> bucket, generated backend config, and GitHub OIDC role. The
> `infrastructure/envs/dev` root uses the generated S3 backend. GitHub
> repository variables and secrets are synced from bootstrap outputs and local
> dev Terraform inputs for the manual AWS OIDC smoke workflow, frontend
> deployment workflows, and provisioning workflows. Frontend deployment supports
> both manual dry-run and manual apply workflows. Terraform provisioning and
> Lambda code deployment remain separate from frontend deployment.

---

## Setup Sequence

Use this order when setting up the project from a fresh clone. The sequence
assumes a `dev` environment and an AWS account where the local AWS CLI identity
is allowed to create the bootstrap resources, provision the environment, and
deploy frontend assets.

1. Clone the repository.
2. Install the required local tools listed in this document:
   - Python
   - Docker
   - Terraform
   - `tflint`
   - `terraform-docs`
   - AWS CLI
   - GitHub CLI
   - Node.js
   - npm
3. Configure AWS CLI credentials for the target AWS account and verify them:
   ```powershell
   aws sts get-caller-identity
   ```
4. Copy and edit the bootstrap variables:
   - `infrastructure/bootstrap/dev/terraform.tfvars.example`
   - `infrastructure/bootstrap/dev/terraform.tfvars`

   The bootstrap variables define the AWS region, project/environment naming,
   GitHub organization/repository, branch-scoped OIDC trust, and optional tags.
5. Initialize, validate, and apply the bootstrap root locally:
   ```powershell
   terraform -chdir=infrastructure/bootstrap/dev init
   terraform -chdir=infrastructure/bootstrap/dev validate -no-color
   terraform -chdir=infrastructure/bootstrap/dev apply
   ```

   This creates the dev Terraform state bucket, generated backend config,
   GitHub Actions OIDC provider, branch-scoped GitHub Actions role, state
   access policy, deploy policies, and permissions boundary.
6. Confirm the generated backend config exists and is ignored by Git:
   - `infrastructure/envs/dev/backend.tf`

   ```powershell
   Get-Content infrastructure/envs/dev/backend.tf
   git status --short --ignored -- infrastructure/envs/dev/backend.tf
   ```
7. Copy and edit the `dev` environment variables:
   - `infrastructure/envs/dev/terraform.tfvars.example`
   - `infrastructure/envs/dev/terraform.tfvars`

   These variables provide environment-specific values such as project email
   addresses and other local deployment inputs that are intentionally not
   committed.
8. Sync GitHub repository variables and secrets for GitHub Actions:
   ```powershell
   python scripts/sync_github_actions_vars.py --dry-run
   python scripts/sync_github_actions_vars.py
   gh variable list
   gh secret list
   ```
9. Package Lambda artifacts for the provisioning lane:
   ```powershell
   python scripts/package_lambdas.py
   ```

   Fresh provisioning requires these ZIP artifacts so Terraform can create
   Lambda functions from the expected package paths. After Lambda functions
   exist, Terraform ignores Lambda package-field drift while continuing to
   manage infrastructure and configuration.
10. Run the manual AWS OIDC smoke workflow from `main` after the repository
    variables have been synced and the workflow file has been merged:
    ```powershell
    gh workflow run aws-oidc-smoke.yml --ref main
    ```

    This confirms that GitHub Actions can assume the AWS role, initialize the
    remote backend, validate `infrastructure/envs/dev`, and access the
    configured remote state bucket and backend key prefix.
11. Run the manual provisioning dry-run workflow from `main`:
    ```powershell
    gh workflow run provisioning-dry-run.yml --ref main
    ```

    This validation-only provisioning dry run uses the synced GitHub variables
    and secrets, generates the dev backend configuration, packages Lambda ZIP
    artifacts, and runs `terraform init`, `terraform validate`, and
    `terraform plan`.

    It does not run `terraform apply`, does not call
    `aws lambda update-function-code`, and does not deploy frontend assets.
12. Run the manual provisioning apply workflow from `main` to create or update
    the `dev` infrastructure:
    ```powershell
    gh workflow run provisioning-apply.yml --ref main -f confirm_apply=apply-dev
    ```

    This manual apply workflow uses the same synced GitHub variables and
    secrets, generates the dev backend configuration, packages Lambda ZIP
    artifacts, runs `terraform init`, `terraform validate`, saves a Terraform
    plan, and applies that saved plan.

    It requires the explicit `confirm_apply=apply-dev` input. It does not call
    `aws lambda update-function-code` and does not deploy frontend assets.
13. Build and deploy the frontend with one of the implemented frontend
    deployment paths.

    For local validation without uploading assets:
    ```powershell
    python scripts/deploy_frontend.py --dry-run
    ```

    For local deployment:
    ```powershell
    python scripts/deploy_frontend.py --apply
    ```

    For GitHub Actions validation from `main`:
    ```powershell
    gh workflow run frontend-deploy-dry-run.yml --ref main
    ```

    For GitHub Actions deployment from `main`:
    ```powershell
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

GitHub Actions uses the OIDC role created by `infrastructure/bootstrap/dev`.
The current OIDC trust is branch-scoped to `main`, so the smoke workflow uses
repository variables and does not use a GitHub Environment.

Before running GitHub Actions workflows, complete the repository variable and
secret sync described in [GitHub Actions Input Sync](#github-actions-input-sync).

The manual `AWS OIDC Smoke` workflow validates:

- GitHub Actions can request an OIDC token
- AWS accepts the token for the branch-scoped role
- the assumed role can access the configured S3 remote state bucket and backend
  key prefix
- Terraform can initialize against the generated S3 backend settings
- Terraform can validate `infrastructure/envs/dev`

The smoke workflow intentionally does not run `terraform plan`, `terraform apply`,
Lambda artifact generation, or frontend deployment. Frontend deployment is
handled by the dedicated frontend workflows. Terraform provisioning and Lambda
artifact generation remain separate.

### Provisioning Dry Run Workflow

The manual provisioning dry-run workflow is:

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

This workflow validates provisioning only. It does not apply infrastructure,
deploy Lambda code, or deploy frontend assets.

### Provisioning Apply Workflow

The manual provisioning apply workflow is:

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

The apply workflow requires explicit confirmation and applies only the saved
Terraform plan. It does not deploy Lambda code through
`aws lambda update-function-code` and does not deploy frontend assets.

### Local Provisioning Alternative

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

## GitHub Actions Input Sync

Local developers can continue to use the untracked dev tfvars file:

- `infrastructure/envs/dev/terraform.tfvars`

GitHub Actions cannot read that local file. The unified sync helper publishes
both bootstrap-derived values and supported dev Terraform inputs into GitHub:

```powershell
python scripts/sync_github_actions_vars.py --dry-run
python scripts/sync_github_actions_vars.py
```

The helper uses Terraform only to read bootstrap outputs. It does not call AWS
directly and does not run Terraform plan/apply. Dry-run mode prints the planned
GitHub variable and secret names without updating GitHub.

The helper sets these dev Terraform repository variables:

- `DEV_PROJECT_NAME`
- `DEV_ENVIRONMENT`
- `DEV_DYNAMODB_POINT_IN_TIME_RECOVERY_ENABLED`
- `DEV_ENABLE_WAF`

The helper sets these dev Terraform repository secrets:

- `DEV_SES_SENDER_EMAIL`
- `DEV_SNS_ADMIN_EMAIL_SUBSCRIPTIONS_JSON`

The same helper also sets these bootstrap-derived repository variables:

- `AWS_ROLE_TO_ASSUME`
- `AWS_REGION`
- `TF_BACKEND_BUCKET`
- `TF_BACKEND_KEY`

Provisioning workflows should pass the GitHub values to Terraform through
`TF_VAR_*` environment variables. The local `terraform.tfvars` file remains
operator-owned and must not be committed.

## Lambda Provisioning and Code Deployment Boundary

Lambda infrastructure ownership is separate from Lambda code deployment, while
Lambda artifact generation remains available to both automation lanes.

- Terraform continues to own Lambda infrastructure, configuration, and service
  wiring.
- Provisioning builds Lambda ZIP artifacts before Terraform plan/apply so
  Terraform can create Lambda functions when needed.
- After Lambda functions exist, Terraform ignores Lambda package-field drift
  while continuing to detect infrastructure and configuration drift.
- Lambda code deployment automation builds Lambda ZIP artifacts, maps workloads
  to existing function names from Terraform outputs, and updates code through
  `aws lambda update-function-code`.
- Lambda code deployment workflows may read Terraform outputs, but they must
  not run `terraform apply`.

Config drift such as environment variables, timeout, memory, tracing, IAM,
event source mappings, and API Gateway wiring must remain visible to Terraform.

### Lambda Code Deployment Helper

The local Lambda code deployment helper is:

- `scripts/deploy_lambdas.py`

The helper is the shared deployment path for Lambda ZIP code updates. It
packages Lambda artifacts, reads deployment values from Terraform outputs in:

- `infrastructure/envs/dev`

Before using the helper, make sure the dev Terraform state is current and
includes the Lambda deployment outputs:

- `aws_region`
- `lambda_function_names`

Run a safe dry-run first from the repository root:

```powershell
python scripts/deploy_lambdas.py --dry-run
```

Dry-run mode:

- packages all deployed Lambda workloads
- reads `terraform output -json`
- validates the workload-to-function mapping
- validates expected ZIP artifacts
- prints the planned `aws lambda update-function-code` commands
- does not update Lambda function code

For a real Lambda code deployment, run:

```powershell
python scripts/deploy_lambdas.py --apply
```

Apply mode uses the same packaging and validation path, then updates existing
Lambda function code with `aws lambda update-function-code`.

The helper does not run `terraform plan`, run `terraform apply`, publish Lambda
versions, manage aliases, use CodeDeploy, or deploy frontend assets.

### Lambda Deployment Dry Run Workflow

The same dry-run path is also available as a manual GitHub Actions workflow:

- `Lambda Deployment Dry Run`
- `.github/workflows/lambda-deploy-dry-run.yml`

Run it from `main` with:

```powershell
gh workflow run lambda-deploy-dry-run.yml --ref main
```

That workflow uses GitHub OIDC, generates the dev backend configuration from
repository variables, initializes and validates the remote Terraform backend,
checks the required Lambda deployment outputs, and then runs:

```powershell
python scripts/deploy_lambdas.py --dry-run
```

The GitHub Actions dry-run workflow follows the same safety boundary: it
packages artifacts and previews Lambda code updates only. It does not run
`terraform plan`, run `terraform apply`, call `aws lambda update-function-code`,
or deploy frontend assets.

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
- AWS CLI is used by local deployment helpers for S3 uploads and CloudFront
  cache invalidation
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

For the current frontend deployment helper, the AWS CLI must be able to access
the same AWS account and permissions used for the dev environment.

The helper uses AWS CLI commands for:

- previewing and syncing `frontend/dist/` to the private frontend S3 bucket
- creating a CloudFront cache invalidation after a real frontend upload

## Frontend Operations

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

Manual GitHub Actions frontend workflows from `main`:

```powershell
gh workflow run frontend-deploy-dry-run.yml --ref main
gh workflow run frontend-deploy-apply.yml --ref main -f confirm_deploy=deploy-dev
```

Frontend deployment uploads static assets to S3 and creates a CloudFront
invalidation in apply mode. It does not run Terraform provisioning, package
Lambda artifacts, or deploy Lambda code.
