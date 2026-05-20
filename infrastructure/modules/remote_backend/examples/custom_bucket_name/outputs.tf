output "state_bucket_name" {
  description = "Name of the S3 bucket created for Terraform state."
  value       = module.remote_backend.state_bucket_name
}

output "state_bucket_arn" {
  description = "ARN of the S3 bucket created for Terraform state."
  value       = module.remote_backend.state_bucket_arn
}

output "state_bucket_regional_domain_name" {
  description = "Regional domain name of the S3 bucket created for Terraform state."
  value       = module.remote_backend.state_bucket_regional_domain_name
}
