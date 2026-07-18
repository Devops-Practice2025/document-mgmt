module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 21.0"

  kubernetes_version = var.kubernetes_version


  name = local.name

  endpoint_public_access  = true
  endpoint_private_access = true

  enable_cluster_creator_admin_permissions = false
  access_entries = {
    cluster_creator = {
      principal_arn = "arn:aws:iam::361769597147:user/open-environment-jkwq8-admin"

      policy_associations = {
        admin = {
          policy_arn = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"

          access_scope = {
            type = "cluster"
          }
        }
      }
    }

    github_actions = {
      principal_arn = "arn:aws:iam::361769597147:role/bankdocs-github-actions"

      policy_associations = {
        admin = {
          policy_arn = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"

          access_scope = {
            type = "cluster"
          }
        }
      }
    }
  }

  kms_key_administrators = [
    "arn:aws:iam::361769597147:user/open-environment-jkwq8-admin",
    "arn:aws:iam::361769597147:role/bankdocs-github-actions"
  ]

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  control_plane_subnet_ids = module.vpc.private_subnets

  addons = {
    coredns = {
      most_recent = true
    }

    kube-proxy = {
      most_recent = true
    }

    vpc-cni = {
      most_recent    = true
      before_compute = true
    }

    metrics-server = {
      most_recent = true
    }
  }

  eks_managed_node_groups = {
    application = {
      ami_type           = "AL2023_x86_64_STANDARD"
      kubernetes_version = var.kubernetes_version

      instance_types = ["t3.medium"]

      min_size     = 1
      desired_size = 2
      max_size     = 3

      subnet_ids = module.vpc.private_subnets

      labels = {
        workload = "application"
      }

      tags = {
        Name = "${local.name}-application-node"
      }
    }
  }
}

resource "aws_vpc_security_group_ingress_rule" "rds_from_eks_nodes" {
  security_group_id = aws_security_group.rds.id

  referenced_security_group_id = module.eks.node_security_group_id

  from_port   = 3306
  to_port     = 3306
  ip_protocol = "tcp"

  description = "MySQL from EKS worker nodes"
}