############################################
# Derived naming and tagging values
############################################

locals {
  # Keep bootstrap resource names aligned with the environment naming baseline.
  name_prefix = "${var.project_name}-${var.environment}"

  # Match the dev environment's baseline tag shape so bootstrap resources are
  # easy to identify in the same account and cost views.
  tags = merge(var.additional_tags, {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  })
}

############################################
# Remote backend values
############################################

locals {
  # Dev bootstrap owns its backend bucket directly so it can stay
  # teardown-friendly. Persistent reusable backend buckets are handled by the
  # remote_backend module.
  state_bucket_name = coalesce(
    var.state_bucket_name,
    "${local.name_prefix}-tf-state-${random_id.bucket_suffix.hex}"
  )

  # Keep the state key aligned with the actual environment root path in this
  # repository. This value is used when generating
  # infrastructure/envs/dev/backend.tf.
  tf_backend_key = "infrastructure/envs/${var.environment}/terraform.tfstate"
}

############################################
# GitHub OIDC trust values
############################################

locals {
  github_repo_full_name = "${var.github_org}/${var.github_repo}"
  github_branch_subject = "repo:${local.github_repo_full_name}:ref:refs/heads/${var.github_branch}"
  oidc_url              = "https://token.actions.githubusercontent.com"
}
