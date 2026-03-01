module "remote_backend" {
  source = "../../modules/remote_backend"

  project_name      = var.project_name
  environment       = var.environment
  common_tags       = var.common_tags
  state_bucket_name = var.state_bucket_name
  lock_table_name   = var.lock_table_name
}


