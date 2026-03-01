output "tf_state_bucket_name" {
  description = "Name of the S3 bucket used for Terraform state."
  value       = module.remote_backend.state_bucket_name
}

output "tf_state_bucket_arn" {
  description = "ARN of the S3 bucket used for Terraform state."
  value       = module.remote_backend.state_bucket_arn
}

output "tf_state_lock_table_name" {
  description = "Name of the DynamoDB table used for Terraform state locking."
  value       = module.remote_backend.lock_table_name
}

output "tf_state_lock_table_arn" {
  description = "ARN of the DynamoDB table used for Terraform state locking."
  value       = module.remote_backend.lock_table_arn
}
