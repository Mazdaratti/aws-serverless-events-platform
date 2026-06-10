# Lambda Packaging

This directory contains the Python Lambda workloads and the shared helper
package under `lambdas/shared`.

Lambda workloads are deployed as deterministic ZIP artifacts built by:

| Helper | Purpose |
|---|---|
| `scripts/package_lambda.py` | Package one workload with optional shared helpers or vendored dependencies |
| `scripts/package_lambdas.py` | Package the complete workload set expected by `infrastructure/envs/dev` |

Deterministic metadata and file ordering prevent unchanged source inputs from
producing noisy artifact differences.

Provisioning and Lambda code deployment both use these artifacts, but packaging
does not provision infrastructure or update AWS resources. Deployment ownership
is documented in
[project-setup.md](../docs/project-setup.md#deployment-boundaries).

## All-Workload Packaging

Build every deployed workload from the repository root:

```powershell
python scripts/package_lambdas.py
```

Artifacts are written to:

```text
artifacts/lambda/<function-key>.zip
```

The orchestration helper:

- validates every configured workload source directory
- rebuilds the Lambda-compatible RSVP authorizer vendor tree
- applies each workload's shared/vendor packaging mode
- verifies every expected ZIP exists
- prints the workload-to-artifact summary

Skip the Docker vendor rebuild only when a compatible, non-empty vendor tree
already exists:

```powershell
python scripts/package_lambdas.py --skip-authorizer-vendor-build
```

Skip mode still validates `lambdas/rsvp_authorizer/vendor/` before packaging.

## Per-Workload Packaging Modes

`scripts/package_lambda.py` packages one source directory and supports three
repository packaging modes:

| Mode | ZIP contents | Workloads |
|---|---|---|
| Source and shared helpers | Workload files at ZIP root and `lambdas/shared` under `shared/...` | API and business workloads |
| Source only | Workload files at ZIP root | `notification-planner`, `notification-sender` |
| Source, shared helpers, and vendor dependencies | Workload files and vendor contents at ZIP root, plus `shared/...` | `rsvp-authorizer` |

### Shared-Helper Example

```powershell
python scripts/package_lambda.py `
  lambdas/get_event `
  artifacts/lambda/get-event.zip
```

Shared helpers are included by default.

### Source-Only Example

Use `--no-shared` for a workload that does not import `lambdas/shared`:

```powershell
python scripts/package_lambda.py `
  lambdas/notification_planner `
  artifacts/lambda/notification-planner.zip `
  --no-shared
```

The all-workload orchestrator applies these modes from its canonical workload
map, so provisioning and deployment automation do not need separate packaging
commands per function.

## RSVP Authorizer Dependencies

The mixed-mode RSVP authorizer directly depends on `PyJWT` and `cryptography`.
The native dependency chain also includes packages such as `cffi`.

| Path | Purpose |
|---|---|
| `lambdas/rsvp_authorizer/requirements.txt` | Tracked dependency source |
| `lambdas/rsvp_authorizer/vendor/` | Generated workload-local dependencies |
| `lambdas/rsvp_authorizer/Dockerfile.vendor` | Lambda-compatible vendor build |

The generated vendor directory is ignored by Git and must not be used as a
shared dependency directory for other workloads.

### Local Test Dependencies

For local authorizer tests, install dependencies into the workload-local vendor
directory:

```powershell
.\.venv\Scripts\python.exe -m pip install `
  --target lambdas/rsvp_authorizer/vendor `
  --requirement lambdas/rsvp_authorizer/requirements.txt
```

This installation supports local imports only. It is not necessarily compatible
with the AWS Lambda Linux runtime.

### Lambda-Compatible Vendor Build

Build deployment dependencies with:

```powershell
python scripts/build_rsvp_authorizer_vendor.py
```

The helper:

- removes the existing vendor directory
- builds the workload-local Docker image
- installs dependencies in a Linux Python 3.13 container
- verifies that the rebuilt vendor directory is non-empty

The resulting dependencies target:

- AWS Lambda Linux
- Python `3.13`
- `x86_64`

This prevents locally built native binaries from being included in the
deployment artifact.

The helper is the preferred build path because it starts from a clean vendor
directory. For lower-level Docker troubleshooting, reproduce that cleanup
before running Docker:

```powershell
Remove-Item `
  -Recurse `
  -Force `
  -ErrorAction SilentlyContinue `
  lambdas/rsvp_authorizer/vendor
```

```powershell
docker build `
  -f lambdas/rsvp_authorizer/Dockerfile.vendor `
  -t rsvp-authorizer-vendor `
  lambdas/rsvp_authorizer
```

```powershell
docker run --rm `
  -v "${PWD}\lambdas\rsvp_authorizer:/output" `
  rsvp-authorizer-vendor
```

### Authorizer Packaging

After building compatible dependencies, package the authorizer with:

```powershell
python scripts/package_lambda.py `
  lambdas/rsvp_authorizer `
  artifacts/lambda/rsvp-authorizer.zip `
  --vendor-dir lambdas/rsvp_authorizer/vendor
```

The vendor contents are placed at ZIP root so the authorizer can import them
directly. The all-workload helper performs this build and packaging sequence
automatically.

## Generated Artifacts

Generated packaging outputs are disposable and ignored by Git:

| Path | Generated by |
|---|---|
| `artifacts/lambda/*.zip` | Lambda packaging helpers |
| `lambdas/rsvp_authorizer/vendor/` | Local dependency install or Docker vendor build |
| `__pycache__/` and `*.pyc` | Python execution |

The authorizer dependency sources remain tracked:

- `lambdas/rsvp_authorizer/requirements.txt`
- `lambdas/rsvp_authorizer/Dockerfile.vendor`

Inspect ignored artifacts from the repository root with:

```powershell
git status --short --ignored -- artifacts lambdas/rsvp_authorizer/vendor
```
