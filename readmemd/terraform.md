No worries! Let's go. 🚀

## Phase 2 — Next Step: Terraform

We'll provision all AWS infrastructure as code in this order:

```
1. S3 bucket (remote Terraform state)
2. VPC + Subnets
3. RDS MySQL
4. EKS Cluster
5. ECR (container registry)
```

***

## Folder structure for Terraform

```bash
mkdir -p /mnt/c/Users/UO85HU/Documents/New_repos/document-mgmt/terraform
cd terraform

# Create these files:
touch main.tf
touch variables.tf
touch outputs.tf
touch vpc.tf
touch rds.tf
touch eks.tf
touch ecr.tf
```

***

## Step 1 — Create S3 bucket for Terraform state first

Before writing any Terraform, create the S3 bucket that stores Terraform's state file. This is best practice — state lives in AWS, not on your laptop.

```bash
aws s3 mb s3://bankdocs-terraform-state-<yourname> --region us-east-1

# Enable versioning (so you can roll back state if something breaks)
aws s3api put-bucket-versioning \
  --bucket bankdocs-terraform-state-<yourname> \
  --versioning-configuration Status=Enabled
```

***

## Step 2 — `main.tf` (provider + remote state)

```hcl
# main.tf

# Tell Terraform we're using AWS
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Store state in S3 instead of local file
  # This is critical for team environments and CI/CD
  backend "s3" {
    bucket = "bankdocs-terraform-state-<yourname>"
    key    = "bankdocs/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
}
```

***

## Step 3 — `variables.tf`

```hcl
# variables.tf

variable "aws_region" {
  default = "us-east-1"
}

variable "project" {
  default = "bankdocs"
}

variable "db_password" {
  description = "RDS MySQL root password"
  sensitive   = true   # won't show in logs
}
```

***

## Do this right now

```bash
cd terraform

# Initialize Terraform — downloads AWS provider
terraform init
```

You should see:
```
Terraform has been successfully initialized!
```

Tell me when `terraform init` succeeds and we move to VPC + EKS. 🚀