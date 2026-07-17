data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  name = "${var.project}-${var.environment}"

  azs = slice(data.aws_availability_zones.available.names, 0, 2)
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 6.0"

  name = local.name
  cidr = var.vpc_cidr

  azs = local.azs

  public_subnets = [
    "10.20.1.0/24",
    "10.20.2.0/24"
  ]

  private_subnets = [
    "10.20.11.0/24",
    "10.20.12.0/24"
  ]

  database_subnets = [
    "10.20.21.0/24",
    "10.20.22.0/24"
  ]

  create_database_subnet_group = true

  enable_nat_gateway = true

  # Development cost optimization.
  # For production, use one NAT gateway per AZ.
  single_nat_gateway = true

  enable_dns_support   = true
  enable_dns_hostnames = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }
}