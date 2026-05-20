output "state_bucket_name" {
  description = "Name of the S3 bucket created for Terraform state."
  value       = aws_s3_bucket.terraform_state.id
}

output "state_bucket_arn" {
  description = "ARN of the S3 bucket created for Terraform state."
  value       = aws_s3_bucket.terraform_state.arn
}

output "state_bucket_regional_domain_name" {
  description = "Regional domain name of the S3 bucket created for Terraform state."
  value       = aws_s3_bucket.terraform_state.bucket_regional_domain_name
}
