output "state_bucket_name" {
  description = "Name of the S3 bucket created for dev Terraform state."
  value       = aws_s3_bucket.terraform_state.id
}

output "state_bucket_arn" {
  description = "ARN of the S3 bucket created for dev Terraform state."
  value       = aws_s3_bucket.terraform_state.arn
}

output "state_backend_key" {
  description = "S3 object key used by the generated dev Terraform backend configuration."
  value       = local.tf_backend_key
}

output "github_oidc_provider_arn" {
  description = "ARN of the GitHub Actions OIDC provider."
  value       = aws_iam_openid_connect_provider.github.arn
}

output "github_actions_role_name" {
  description = "Name of the GitHub Actions OIDC role."
  value       = aws_iam_role.github_actions.name
}

output "github_actions_role_arn" {
  description = "ARN of the GitHub Actions OIDC role."
  value       = aws_iam_role.github_actions.arn
}

output "github_actions_state_policy_arn" {
  description = "ARN of the IAM policy granting GitHub Actions access to the dev Terraform state backend."
  value       = aws_iam_policy.github_actions_state.arn
}

output "github_actions_deploy_policy_arn" {
  description = "ARN of the IAM policy granting GitHub Actions scoped Terraform deployment permissions for dev."
  value       = aws_iam_policy.github_actions_deploy.arn
}

output "github_actions_permissions_boundary_policy_arn" {
  description = "ARN of the optional GitHub Actions permissions boundary policy, or null when disabled."
  value       = var.create_permissions_boundary ? aws_iam_policy.github_actions_boundary[0].arn : null
}
