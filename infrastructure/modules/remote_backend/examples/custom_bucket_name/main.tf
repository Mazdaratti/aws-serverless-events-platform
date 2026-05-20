############################################
# Provider configuration
############################################

provider "aws" {
  region = "eu-central-1"
}

############################################
# Custom bucket name example
############################################

module "remote_backend" {
  source = "../.."

  # Persistent environments often use an explicitly chosen backend bucket name
  # so operators can align naming with account-level conventions. This example
  # remains documentation-safe and should be changed before applying for real.
  name_prefix       = "aws-serverless-events-platform-example"
  state_bucket_name = "example-aws-serverless-events-platform-tf-state"

  tags = {
    Project      = "aws-serverless-events-platform"
    Environment  = "example"
    ManagedBy    = "Terraform"
    Module       = "remote_backend"
    CriticalData = "true"
  }
}
