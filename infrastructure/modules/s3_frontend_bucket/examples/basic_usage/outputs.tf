############################################
# Example outputs
############################################

output "bucket_arn" {
  description = "ARN of the private frontend origin bucket created by the example."
  value       = module.s3_frontend_bucket.bucket_arn
}

output "bucket_id" {
  description = "ID of the private frontend origin bucket created by the example."
  value       = module.s3_frontend_bucket.bucket_id
}

output "bucket_name" {
  description = "Name of the private frontend origin bucket created by the example."
  value       = module.s3_frontend_bucket.bucket_name
}

output "bucket_regional_domain_name" {
  description = "Regional domain name of the private frontend origin bucket created by the example."
  value       = module.s3_frontend_bucket.bucket_regional_domain_name
}
