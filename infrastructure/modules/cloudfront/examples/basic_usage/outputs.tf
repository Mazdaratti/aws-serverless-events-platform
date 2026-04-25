############################################
# Example outputs
############################################

output "distribution_id" {
  description = "ID of the CloudFront distribution created by the example."
  value       = module.cloudfront.distribution_id
}

output "distribution_arn" {
  description = "ARN of the CloudFront distribution created by the example."
  value       = module.cloudfront.distribution_arn
}

output "distribution_domain_name" {
  description = "Domain name of the CloudFront distribution created by the example."
  value       = module.cloudfront.distribution_domain_name
}

output "distribution_hosted_zone_id" {
  description = "Route 53 hosted zone ID used by the CloudFront distribution created by the example."
  value       = module.cloudfront.distribution_hosted_zone_id
}

output "spa_rewrite_function_arn" {
  description = "ARN of the CloudFront Function that rewrites eligible /app SPA navigations."
  value       = module.cloudfront.spa_rewrite_function_arn
}

output "spa_rewrite_function_name" {
  description = "Name of the CloudFront Function that rewrites eligible /app SPA navigations."
  value       = module.cloudfront.spa_rewrite_function_name
}

output "s3_origin_access_control_id" {
  description = "ID of the Origin Access Control created by the example."
  value       = module.cloudfront.s3_origin_access_control_id
}

output "frontend_bucket_name" {
  description = "Name of the private frontend bucket created by the example."
  value       = aws_s3_bucket.frontend.bucket
}

output "api_origin_domain_name" {
  description = "API Gateway origin domain name passed into the CloudFront module."
  value       = replace(aws_apigatewayv2_api.example.api_endpoint, "https://", "")
}

output "api_origin_path" {
  description = "API Gateway stage path passed into the CloudFront module."
  value       = "/${aws_apigatewayv2_stage.example.name}"
}
