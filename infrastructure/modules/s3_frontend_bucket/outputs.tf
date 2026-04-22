############################################
# Downstream bucket outputs
############################################

output "bucket_arn" {
  description = "ARN of the private frontend origin bucket."
  value       = aws_s3_bucket.this.arn
}

output "bucket_id" {
  description = "ID of the private frontend origin bucket."
  value       = aws_s3_bucket.this.id
}

output "bucket_name" {
  description = "Name of the private frontend origin bucket."
  value       = aws_s3_bucket.this.bucket
}

output "bucket_regional_domain_name" {
  description = "Regional domain name of the private frontend origin bucket."
  value       = aws_s3_bucket.this.bucket_regional_domain_name
}
