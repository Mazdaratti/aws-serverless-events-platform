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
> repository variables are synced from bootstrap outputs for the manual AWS OIDC
> smoke workflow and frontend deployment workflows. Frontend deployment supports
> both manual dry-run and manual apply workflows. Terraform provisioning and
> Lambda artifact generation remain separate from frontend deployment.

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
5. Initialize, validate, and apply the bootstrap root:
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
7. Sync GitHub repository variables for GitHub Actions from bootstrap outputs:
   ```powershell
   python scripts/sync_github_actions_vars.py --dry-run
   python scripts/sync_github_actions_vars.py
   gh variable list
   ```
8. Initialize `infrastructure/envs/dev` with the generated remote backend:
   ```powershell
   terraform -chdir=infrastructure/envs/dev init
   terraform -chdir=infrastructure/envs/dev validate -no-color
   ```
9. Run the manual AWS OIDC smoke workflow from `main` after the repository
   variables have been synced and the workflow file has been merged.

   This confirms that GitHub Actions can assume the AWS role, initialize the
   remote backend, validate `infrastructure/envs/dev`, and read Terraform
   outputs from remote state.
10. Copy and edit the `dev` environment variables:
   - `infrastructure/envs/dev/terraform.tfvars.example`
   - `infrastructure/envs/dev/terraform.tfvars`

   These variables provide environment-specific values such as project email
   addresses and other local deployment inputs that are intentionally not
   committed.
11. Package Lambda artifacts before provisioning Lambda-backed infrastructure.
   Use the packaging instructions in `lambdas/README.md` so Terraform can deploy
   the expected ZIP artifacts for the current Lambda artifact layout.
12. Provision the `dev` environment:
   ```powershell
   terraform -chdir=infrastructure/envs/dev plan -out=tfplan
   terraform -chdir=infrastructure/envs/dev apply tfplan
   terraform -chdir=infrastructure/envs/dev plan
   ```

   The final plan should report no changes after a successful apply.
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

Sync the required repository variables from the bootstrap outputs:

```powershell
python scripts/sync_github_actions_vars.py --dry-run
python scripts/sync_github_actions_vars.py
```

The helper sets these repository variables:

- `AWS_ROLE_TO_ASSUME`
- `AWS_REGION`
- `TF_BACKEND_BUCKET`
- `TF_BACKEND_KEY`

Verify the repository variables with:

```powershell
gh variable list
```

The manual `AWS OIDC Smoke` workflow validates:

- GitHub Actions can request an OIDC token
- AWS accepts the token for the branch-scoped role
- the assumed role can read the S3 remote state object
- Terraform can initialize against the generated S3 backend settings
- Terraform can validate `infrastructure/envs/dev`
- Terraform can read `envs/dev` outputs from remote state

The smoke workflow intentionally does not run `terraform plan`, `terraform apply`,
Lambda artifact generation, or frontend deployment. Frontend deployment is
handled by the dedicated frontend workflows. Terraform provisioning and Lambda
artifact generation remain separate.

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

## Frontend

The frontend application uses:

- Node.js
- npm
- React
- Vite
- TypeScript
- React Router
- Tailwind CSS

The frontend app lives under:

- `frontend/`

Local frontend validation should run from that directory:

- `npm ci`
- `npm run typecheck`
- `npm run build`
- `npm run test`
- `npm run test:e2e`
- `npm run dev` (optional for local development)

Use `npm ci` for PR validation because `frontend/package-lock.json` is now
committed and represents the reproducible dependency install plan.

The current frontend automated testing baseline uses:

- Vitest
- React Testing Library
- `@testing-library/jest-dom`
- `jsdom`
- Playwright
- Chromium browser runtime installed with:
  - `npx playwright install chromium`

These tests run locally without AWS, Cognito, CloudFront, or backend
dependencies and should be included in frontend validation for component,
interaction, and browser smoke changes.

For local browser testing, copy the example environment file and provide the
public Cognito values for the active environment:

- `frontend/.env.example`
- `frontend/.env`

Only public `VITE_*` values belong in the frontend environment file. Do not add
API Gateway invoke URLs or secrets.

The frontend is built as a static SPA for the CloudFront/S3 delivery model.

Runtime routing and API integration rules:

- React Router uses `BrowserRouter` with `/app` as the basename
- Vite must not configure `base: "/app/"`; default base (root) must be used
- static build assets should resolve as root-relative paths such as
  `/assets/...`
- API calls must use same-origin relative paths such as `/events`
- API calls must not use a direct API Gateway URL
- API calls must not use a `/api` prefix

Local Vite development intentionally keeps the same-origin `/events` API model
and does not add a development proxy.

The current Playwright browser smoke baseline runs locally against the Vite dev
server and covers:

- app-shell rendering under `/app`
- public events route shell rendering
- protected-route prompt rendering for `/app/my-events`

### Frontend Deployment Helper

The local frontend deployment helper is:

- `scripts/deploy_frontend.py`

The helper is the shared deployment path for the React/Vite frontend. It is used
for local deployment and by the manual GitHub Actions frontend workflows. It
reads public frontend deployment values from Terraform outputs in:

- `infrastructure/envs/dev`

Before using the helper, make sure the dev Terraform state is current and
includes the frontend deployment outputs:

- `aws_region`
- `frontend_bucket_name`
- `cloudfront_distribution_id`
- `cloudfront_distribution_domain_name`
- `cognito_user_pool_id`
- `cognito_user_pool_client_id`

Run a safe dry-run first from the repository root:

```bash
python scripts/deploy_frontend.py --dry-run
```

The same dry-run path is also available as a manual GitHub Actions workflow:

- `Frontend Deployment Dry Run`
- `.github/workflows/frontend-deploy-dry-run.yml`

Run it from `main` with:

```powershell
gh workflow run frontend-deploy-dry-run.yml --ref main
```

That workflow has been validated from `main`. It uses GitHub OIDC, generates
the dev backend configuration from repository variables, initializes the remote
Terraform backend, checks the required frontend deployment outputs, and then
runs:

```bash
python scripts/deploy_frontend.py --dry-run
```

Dry-run mode:

- reads `terraform output -json`
- writes a temporary `frontend/.env.production.local`
- injects only approved public `VITE_*` values
- runs `npm ci`
- runs `npm run typecheck`
- runs `npm run build`
- does not run frontend browser or component tests yet
- verifies `frontend/dist/` exists
- previews the S3 upload with `aws s3 sync --dryrun`
- does not upload files
- does not invalidate CloudFront

The GitHub Actions dry-run workflow follows the same safety boundary: it builds
and previews deployment only. It does not upload frontend assets and does not
create a CloudFront invalidation.

For a real frontend deployment, run:

```bash
python scripts/deploy_frontend.py --apply
```

The same apply path is also available as a manual GitHub Actions workflow:

- `Frontend Deployment Apply`
- `.github/workflows/frontend-deploy-apply.yml`

Run it from `main` with the required confirmation input:

```powershell
gh workflow run frontend-deploy-apply.yml --ref main -f confirm_deploy=deploy-dev
```

That workflow has been validated from `main`. It uses GitHub OIDC, generates
the dev backend configuration from repository variables, initializes the remote
Terraform backend, validates the `dev` environment root, checks the required
frontend deployment outputs, and then runs:

```bash
python scripts/deploy_frontend.py --apply
```

Apply mode performs the same validation and S3 dry-run first, then:

- syncs `frontend/dist/` to the private frontend S3 bucket with `--delete`
- creates a CloudFront invalidation for `/*`
- prints the CloudFront frontend URLs to validate

The manual apply workflow follows the same deployment boundary: it uploads
frontend assets and creates the CloudFront invalidation, but it does not run
`terraform plan`, run `terraform apply`, provision infrastructure, package
Lambda artifacts, or deploy Lambda code.

The helper writes only these public browser build values:

- `VITE_AWS_REGION`
- `VITE_COGNITO_USER_POOL_ID`
- `VITE_COGNITO_USER_POOL_CLIENT_ID`

Do not add an API Gateway URL, secrets, AWS credentials, or non-public
configuration to frontend Vite environment files.

The helper restores any existing `frontend/.env.production.local` file after
the build. If that file did not exist before the helper ran, it is removed.

After a real deployment, validate through CloudFront:

- `https://<cloudfront-domain>/app`
- `https://<cloudfront-domain>/app/events`
- `https://<cloudfront-domain>/app/my-events`
- `https://<cloudfront-domain>/app/create-event`
- `https://<cloudfront-domain>/app/events/<event-id>`
- `https://<cloudfront-domain>/app/events/<event-id>/rsvps`
- `https://<cloudfront-domain>/events`

Also refresh a frontend deep link directly in the browser, such as:

- `https://<cloudfront-domain>/app/events`

The refresh should return the SPA entrypoint through CloudFront. API routes
under `/events` should continue to return API responses, not frontend HTML.

For a quick frontend smoke test after deployment, also verify:

- keyboard access to the skip link, navigation, filters, forms, and destructive
  confirmation flows
- sign-in redirects back to protected frontend destinations such as
  `/app/my-events`, event detail pages, and RSVP list pages

Authentication uses Cognito through the frontend Amplify Auth SDK.

Token rules:

- Cognito auth tokens must use `sessionStorage`
- Cognito auth tokens must not use `localStorage`
- the frontend must use the JWT type currently validated by API Gateway and the
  RSVP authorizer, expected to be the Cognito ID token
- the anonymous RSVP token may use `localStorage` because it is not an auth
  token
