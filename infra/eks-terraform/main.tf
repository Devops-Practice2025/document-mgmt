# main.tf

# Tell Terraform we're using AWS
terraform {
  required_version = ">= 1.11.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.52.0, < 7.0.0"
    }
  }

  # Store state in S3 instead of local file
  # This is critical for team environments and CI/CD
  backend "s3" {
    bucket       = "bankdocs-terraform-state-techkarthi"
    key          = "bankdocs/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = false
    use_lockfile = true
  }
}

provider "aws" {
  region = var.aws_region
}