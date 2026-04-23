############################################
# Downstream Web ACL outputs
############################################

output "web_acl_arn" {
  description = "ARN of the CloudFront-scoped Web ACL."
  value       = aws_wafv2_web_acl.this.arn
}

output "web_acl_id" {
  description = "ID of the CloudFront-scoped Web ACL."
  value       = aws_wafv2_web_acl.this.id
}

output "web_acl_name" {
  description = "Name of the CloudFront-scoped Web ACL."
  value       = aws_wafv2_web_acl.this.name
}
