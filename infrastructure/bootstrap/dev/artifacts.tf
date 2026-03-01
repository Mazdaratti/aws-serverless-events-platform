resource "local_file" "backend_config" {
  filename = "${path.module}/../../envs/${var.environment}/backend.tf"

  content = <<EOT
terraform {
  backend "s3" {
    bucket         = "${module.remote_backend.state_bucket_name}"
    dynamodb_table = "${module.remote_backend.lock_table_name}"
    key            = "terraform.tfstate"
    region         = "${var.aws_region}"
  }
}
EOT
}
