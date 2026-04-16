# Lambda Packaging

This directory contains the Python Lambda workload source folders plus the
shared helper package under `lambdas/shared`.

Lambda deployment artifacts in this repository are ZIP files built with:

- `scripts/package_lambda.py`

The script keeps packaging deterministic so repeated builds do not create noisy
artifact differences when the inputs have not changed.

## Standard Packaging Model

For ordinary Lambda workloads, the packaging flow is:

1. package the selected Lambda source directory
2. include `lambdas/shared`
3. write the ZIP artifact under `artifacts/lambda/`

This is the default packaging model currently used by the existing business
Lambdas.

Example:

```powershell
python scripts/package_lambda.py `
  lambdas/get_event `
  artifacts/lambda/get-event.zip
```

The resulting ZIP places:

- the workload source files at ZIP root
- the shared helpers under `shared/...`

## Mixed-Mode Authorizer Exception

The dedicated mixed-mode RSVP authorizer has one extra packaging requirement:

- third-party JWT verification dependencies

For this workload, the tracked dependency source of truth is:

- `lambdas/rsvp_authorizer/requirements.txt`

The generated vendor directory is:

- `lambdas/rsvp_authorizer/vendor/`

That vendor directory is:

- generated
- workload-local
- ignored by Git

It must not become a shared dependency bucket for other Lambdas.

## Local Test Install

For local unit tests, dependencies can be installed into the workload-local
vendor directory so the handler test file can import them directly.

Example:

```powershell
.\.venv\Scripts\python.exe -m pip install `
  --target lambdas/rsvp_authorizer/vendor `
  --requirement lambdas/rsvp_authorizer/requirements.txt
```

This supports local importability for:

- `PyJWT`
- `cryptography`

## Lambda-Compatible Vendor Build

Local importability is not the same as Lambda-runtime compatibility.

The final vendored dependency tree used for deployment must be built for the
deployed Lambda runtime and architecture.

Current locked deployment target:

- Python `3.13`
- `x86_64`
- AWS Lambda Linux runtime

Before rebuilding the vendor tree, remove any previous generated contents so
platform-specific files do not get mixed together.

```powershell
Remove-Item -Recurse -Force lambdas/rsvp_authorizer/vendor
```

Preferred first deployment build approach:

```powershell
.\.venv\Scripts\python.exe -m pip install `
  --target lambdas/rsvp_authorizer/vendor `
  --requirement lambdas/rsvp_authorizer/requirements.txt `
  --platform manylinux2014_x86_64 `
  --implementation cp `
  --python-version 3.13 `
  --only-binary=:all:
```

Why this differs from the local test install:

- local test install only needs the dependencies to import on the local machine
- deployment build must produce a dependency tree compatible with:
  - AWS Lambda Linux
  - Python `3.13`
  - `x86_64`

If this wheel-based build cannot resolve compatible artifacts for the pinned
dependencies, the fallback is to build the vendor tree in a Linux environment
that matches the Lambda target more closely.

Native dependencies such as `cryptography` and `cffi` must match the Lambda
runtime target. A vendor tree built only for local Windows use may package
successfully but still fail at runtime in Lambda.

## Authorizer Packaging Command

When the `vendor/` directory contains the correct Lambda-compatible dependency
build, package the authorizer with:

```powershell
python scripts/package_lambda.py `
  lambdas/rsvp_authorizer `
  artifacts/lambda/rsvp-authorizer.zip `
  --vendor-dir lambdas/rsvp_authorizer/vendor
```

With `--vendor-dir`, vendored dependency contents are placed at ZIP root so the
authorizer can import them directly.

## Cleanup Notes

Generated packaging and dependency artifacts must not be committed.

Examples of generated Lambda-related artifacts:

- `lambdas/rsvp_authorizer/vendor/`
- `artifacts/lambda/*.zip`
- Python cache directories such as `__pycache__`
