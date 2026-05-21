############################################
# GitHub Actions permissions boundary
############################################

resource "aws_iam_policy" "github_actions_boundary" {
  count = var.create_permissions_boundary ? 1 : 0

  name        = "gh-oidc-${local.name_prefix}-boundary"
  description = "Repo-aligned permissions boundary for the GitHub Actions OIDC role."

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "AllowAllWithinBoundaryUnlessExplicitlyDenied"
        Effect   = "Allow"
        Action   = "*"
        Resource = "*"
      },
      {
        Sid    = "DenyIAMUserAndAccessKeyManagement"
        Effect = "Deny"
        Action = [
          "iam:AttachUserPolicy",
          "iam:CreateAccessKey",
          "iam:CreateUser",
          "iam:DeleteAccessKey",
          "iam:DeleteUser",
          "iam:DeleteUserPolicy",
          "iam:DetachUserPolicy",
          "iam:PutUserPolicy",
          "iam:UpdateUser"
        ]
        Resource = "*"
      },
      {
        Sid    = "DenyIAMManagementOutsideProjectScope"
        Effect = "Deny"
        Action = [
          "iam:AttachRolePolicy",
          "iam:CreatePolicy",
          "iam:CreatePolicyVersion",
          "iam:CreateRole",
          "iam:DeletePolicy",
          "iam:DeletePolicyVersion",
          "iam:DeleteRole",
          "iam:DeleteRolePolicy",
          "iam:DetachRolePolicy",
          "iam:PassRole",
          "iam:PutRolePolicy",
          "iam:SetDefaultPolicyVersion",
          "iam:TagPolicy",
          "iam:TagRole",
          "iam:UntagPolicy",
          "iam:UntagRole",
          "iam:UpdateAssumeRolePolicy",
          "iam:UpdateRole"
        ]
        NotResource = [
          "arn:aws:iam::*:role/${local.name_prefix}-*",
          "arn:aws:iam::*:role/gh-oidc-${local.name_prefix}*",
          "arn:aws:iam::*:policy/${local.name_prefix}-*",
          "arn:aws:iam::*:policy/gh-oidc-${local.name_prefix}*"
        ]
      }
    ]
  })

  tags = {
    Name = "gh-oidc-${local.name_prefix}-boundary"
  }
}
