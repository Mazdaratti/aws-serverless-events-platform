############################################
# Example verification outputs
############################################

output "role_names" {
  description = "Rendered IAM role names created by the basic_usage example."
  value       = module.iam.role_names
}

output "role_arns" {
  description = "Rendered IAM role ARNs created by the basic_usage example."
  value       = module.iam.role_arns
}
