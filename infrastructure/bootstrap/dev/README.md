# Bootstrap (dev)

This folder contains the one-time bootstrap stack for remote Terraform state in `dev`.

It provisions:
- S3 bucket for Terraform state
- DynamoDB table for state locking

## Why this stack exists

Terraform cannot use a remote backend until that backend already exists.
So we bootstrap backend resources first, then configure `infrastructure/envs/dev` to use them.

## Usage

```bash
cd infrastructure/bootstrap/dev
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply -var-file=terraform.tfvars
```

After apply, backend configuration is generated automatically at:
- `infrastructure/envs/dev/backend.tf`
