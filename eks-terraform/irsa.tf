data "aws_iam_policy_document" "bankdocs_backend_irsa_trust" {
  statement {
    sid     = "AllowEKSWebIdentityAssumeRole"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [module.eks.oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:sub"
      values   = ["system:serviceaccount:bankdocs:bankdocs-backend"]
    }
  }
}

data "aws_iam_policy_document" "bankdocs_backend_s3_policy" {
  statement {
    sid    = "AllowBucketLevelAccess"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation"
    ]
    resources = [
      "arn:aws:s3:::${aws_s3_bucket.documents.bucket}"
    ]
  }

  statement {
    sid    = "AllowObjectLevelAccess"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject"
    ]
    resources = [
      "arn:aws:s3:::${aws_s3_bucket.documents.bucket}/*"
    ]
  }
}

resource "aws_iam_role" "bankdocs_backend_irsa" {
  name               = "${var.project}-${var.environment}-backend-irsa"
  assume_role_policy = data.aws_iam_policy_document.bankdocs_backend_irsa_trust.json
}

resource "aws_iam_role_policy" "bankdocs_backend_s3" {
  name   = "${var.project}-${var.environment}-backend-s3"
  role   = aws_iam_role.bankdocs_backend_irsa.id
  policy = data.aws_iam_policy_document.bankdocs_backend_s3_policy.json
}

output "backend_irsa_role_arn" {
  value = aws_iam_role.bankdocs_backend_irsa.arn
}