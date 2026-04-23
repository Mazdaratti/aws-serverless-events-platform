############################################
# Example outputs
############################################

output "web_acl_arn" {
  description = "ARN of the CloudFront-scoped Web ACL created by the example."
  value       = module.waf.web_acl_arn
}

output "web_acl_id" {
  description = "ID of the CloudFront-scoped Web ACL created by the example."
  value       = module.waf.web_acl_id
}

output "web_acl_name" {
  description = "Name of the CloudFront-scoped Web ACL created by the example."
  value       = module.waf.web_acl_name
}
