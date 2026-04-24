############################################
# Downstream distribution outputs
############################################

output "distribution_id" {
  description = "ID of the CloudFront distribution."
  value       = aws_cloudfront_distribution.this.id
}

output "distribution_arn" {
  description = "ARN of the CloudFront distribution."
  value       = aws_cloudfront_distribution.this.arn
}

output "distribution_domain_name" {
  description = "Domain name of the CloudFront distribution."
  value       = aws_cloudfront_distribution.this.domain_name
}

output "distribution_hosted_zone_id" {
  description = "Route 53 hosted zone ID used by CloudFront distributions."
  value       = aws_cloudfront_distribution.this.hosted_zone_id
}

############################################
# Downstream origin access outputs
############################################

output "s3_origin_access_control_id" {
  description = "ID of the Origin Access Control used for the private S3 frontend origin."
  value       = aws_cloudfront_origin_access_control.s3.id
}
