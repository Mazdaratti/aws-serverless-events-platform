locals {
  enforced_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }

  merged_tags = merge(var.common_tags, local.enforced_tags)

  generated_state_bucket_name = "${var.project_name}-${var.environment}-tf-state-${random_id.bucket_suffix.hex}"
  generated_lock_table_name   = "${var.project_name}-${var.environment}-tf-lock"

  effective_state_bucket_name = var.state_bucket_name != null ? var.state_bucket_name : local.generated_state_bucket_name
  effective_lock_table_name   = var.lock_table_name != null ? var.lock_table_name : local.generated_lock_table_name
}
