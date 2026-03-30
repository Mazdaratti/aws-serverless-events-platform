############################################
# Lambda execution role outputs
############################################

output "role_names" {
  description = "Map of logical workload key to rendered IAM role name."
  value = {
    for workload_key, role in aws_iam_role.workload :
    workload_key => role.name
  }
}

output "role_arns" {
  description = "Map of logical workload key to rendered IAM role ARN."
  value = {
    for workload_key, role in aws_iam_role.workload :
    workload_key => role.arn
  }
}
