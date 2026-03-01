# Remote Backend Module

Creates Terraform remote backend infrastructure on AWS:
- S3 bucket for state
- DynamoDB table for state locking

## Usage

```hcl
module "remote_backend" {
  source = "../../modules/remote_backend"

  project_name = "aws-serverless-events-platform"
  environment  = "dev"
  common_tags  = {
    Owner = "platform"
  }
}
```
