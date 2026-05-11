############################################
# AWS account context
############################################

# The dev root uses account and partition data to derive deterministic ARNs for
# resources whose names are already fixed by the environment naming convention.
# This keeps module dependencies explicit and avoids using one module output
# only to reconstruct an ARN that Terraform can derive from stable context.
data "aws_caller_identity" "current" {}

# Partition keeps derived ARNs portable across standard AWS and future
# partition-specific deployments.
data "aws_partition" "current" {}
