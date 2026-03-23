# Keep Terraform and provider version constraints in one place so the
# environment root has a clear and predictable toolchain baseline.
terraform {
  required_version = "~> 1.14.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.37"
    }
  }
}
