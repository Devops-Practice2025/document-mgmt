import os
os.makedirs('output', exist_ok=True)

content = r'''# BankDocs on AWS: Terraform Step-by-Step for RHEL VMs

## Overview

This README walks through building the BankDocs 3-tier infrastructure on AWS using Terraform, one step at a time. Each step includes: what you are building, why it matters, the exact Terraform code, how to `apply` it, and how to verify it in both the **AWS Console** and the **AWS CLI**. At the end you will have 3 RHEL EC2 instances (frontend, backend, mysql) with correct networking and security groups, fully destroyable in one command.

---

## Prerequisites

```bash
# Verify AWS CLI is configured
aws sts get-caller-identity

# Verify Terraform is installed
terraform -version
```

Create a working folder:

```bash
mkdir -p ~/bankdocs-aws-tf
cd ~/bankdocs-aws-tf
```

---

## Step 1 — Provider and Backend

### What you're building
The Terraform provider block tells Terraform which cloud (AWS) and region to talk to.

### Create `versions.tf`

```hcl
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
```

### Create `provider.tf`

```hcl
provider "aws" {
  region = var.aws_region
}
```

### Create `variables.tf`

```hcl
variable "aws_region" {
  default = "us-east-1"
}

variable "project" {
  default = "bankdocs"
}

variable "instance_type" {
  default = "t3.medium"
}

# RHEL 9 AMI differs per region - update if your region changes
variable "rhel_ami" {
  default = "ami-0230bd60aa48260c6" # RHEL 9, us-east-1 (verify current AMI ID before use)
}

variable "key_name" {
  description = "Existing EC2 key pair name for SSH access"
  type        = string
}
```

### Apply this step

```bash
terraform init
```

### What to expect
```
Terraform has been successfully initialized!
```

### Learning note
`terraform init` downloads the AWS provider plugin and prepares the working directory. Run this once per new project or whenever you add a new provider.

---

## Step 2 — VPC and Subnet

### What you're building
A private network boundary (VPC) and one public subnet where all 3 VMs will live.

### Create `network.tf`

```hcl
resource "aws_vpc" "main" {
  cidr_block           = "10.20.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.project}-vpc"
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project}-igw"
  }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block               = "10.20.1.0/24"
  map_public_ip_on_launch = true
  availability_zone        = "${var.aws_region}a"

  tags = {
    Name = "${var.project}-public-subnet"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name = "${var.project}-public-rt"
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}
```

### Apply this step

```bash
terraform plan
terraform apply
```

Type `yes` when prompted.

### Verify in AWS Console
1. Open **VPC Console**.
2. Go to **Your VPCs** — confirm `bankdocs-vpc` exists with CIDR `10.20.0.0/16`.
3. Go to **Subnets** — confirm `bankdocs-public-subnet` exists.
4. Go to **Internet Gateways** — confirm it is attached to the VPC.

### Verify with AWS CLI

```bash
aws ec2 describe-vpcs --filters "Name=tag:Name,Values=bankdocs-vpc"

aws ec2 describe-subnets --filters "Name=tag:Name,Values=bankdocs-public-subnet"

aws ec2 describe-internet-gateways --filters "Name=tag:Name,Values=bankdocs-igw"
```

### Learning note
A VPC is your isolated network in AWS. The internet gateway lets resources inside the VPC reach the public internet. The route table decides where outbound traffic goes — `0.0.0.0/0` means "everything else goes to the internet gateway."

---

## Step 3 — Security Groups (Firewall Rules)

### What you're building
Three security groups — one per tier — so only the correct traffic reaches each VM.

### Create `security_groups.tf`

```hcl
resource "aws_security_group" "frontend_sg" {
  name        = "${var.project}-frontend-sg"
  description = "Allow HTTP/HTTPS and SSH to frontend"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # restrict to your IP in real use
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project}-frontend-sg" }
}

resource "aws_security_group" "backend_sg" {
  name        = "${var.project}-backend-sg"
  description = "Allow API traffic only from frontend, SSH from admin"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "API from frontend"
    from_port        = 8080
    to_port          = 8080
    protocol         = "tcp"
    security_groups  = [aws_security_group.frontend_sg.id]
  }

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # restrict to your IP in real use
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project}-backend-sg" }
}

resource "aws_security_group" "mysql_sg" {
  name        = "${var.project}-mysql-sg"
  description = "Allow MySQL only from backend, SSH from admin"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "MySQL from backend"
    from_port        = 3306
    to_port          = 3306
    protocol         = "tcp"
    security_groups  = [aws_security_group.backend_sg.id]
  }

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # restrict to your IP in real use
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project}-mysql-sg" }
}
```

### Apply this step

```bash
terraform plan
terraform apply
```

### Verify in AWS Console
1. Open **EC2 Console > Security Groups**.
2. Confirm 3 groups exist: `bankdocs-frontend-sg`, `bankdocs-backend-sg`, `bankdocs-mysql-sg`.
3. Click `bankdocs-mysql-sg` and confirm inbound rule allows port 3306 only from `bankdocs-backend-sg`.

### Verify with AWS CLI

```bash
aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=bankdocs-frontend-sg,bankdocs-backend-sg,bankdocs-mysql-sg" \
  --query "SecurityGroups[*].{Name:GroupName,ID:GroupId}"
```

### Learning note
Security groups referencing other security groups (instead of raw IPs) is a best practice — it means the rule automatically stays correct even if instances get replaced or IPs change. This is exactly how a real bank would isolate the database tier.

---

## Step 4 — The 3 EC2 Instances

### What you're building
The actual RHEL virtual machines for frontend, backend, and mysql.

### Create `instances.tf`

```hcl
resource "aws_instance" "frontend" {
  ami                    = var.rhel_ami
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.frontend_sg.id]

  tags = { Name = "${var.project}-frontend" }
}

resource "aws_instance" "backend" {
  ami                    = var.rhel_ami
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.backend_sg.id]

  tags = { Name = "${var.project}-backend" }
}

resource "aws_instance" "mysql" {
  ami                    = var.rhel_ami
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.mysql_sg.id]

  tags = { Name = "${var.project}-mysql" }
}
```

### Create `outputs.tf`

```hcl
output "frontend_public_ip" {
  value = aws_instance.frontend.public_ip
}

output "backend_public_ip" {
  value = aws_instance.backend.public_ip
}

output "mysql_public_ip" {
  value = aws_instance.mysql.public_ip
}
```

### Create `terraform.tfvars`

```hcl
aws_region    = "us-east-1"
project       = "bankdocs"
instance_type = "t3.medium"
key_name      = "YOUR_EXISTING_KEY_PAIR_NAME"
```

### Apply this step

```bash
terraform plan
terraform apply
```

Type `yes` when prompted. Wait for the 3 instances to be created (usually under 1 minute).

### What to expect

```
Outputs:

backend_public_ip  = "x.x.x.x"
frontend_public_ip = "x.x.x.x"
mysql_public_ip    = "x.x.x.x"
```

### Verify in AWS Console
1. Open **EC2 Console > Instances**.
2. Confirm 3 running instances: `bankdocs-frontend`, `bankdocs-backend`, `bankdocs-mysql`.
3. Click each instance and confirm the correct security group is attached.
4. Confirm the AMI shows RHEL 9 in the details panel.

### Verify with AWS CLI

```bash
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=bankdocs-frontend,bankdocs-backend,bankdocs-mysql" \
  --query "Reservations[*].Instances[*].{Name:Tags[?Key=='Name']|[0].Value,State:State.Name,PublicIP:PublicIpAddress,Type:InstanceType}" \
  --output table
```

### Learning note
Each `aws_instance` resource maps to exactly one EC2 VM. The `vpc_security_group_ids` attaches the correct firewall to each tier — this is what enforces your "only backend can talk to mysql" rule at the network level.

---

## Step 5 — SSH In and Confirm

### Test connectivity

```bash
# Frontend
ssh -i /path/to/key.pem ec2-user@$(terraform output -raw frontend_public_ip)

# Backend
ssh -i /path/to/key.pem ec2-user@$(terraform output -raw backend_public_ip)

# MySQL
ssh -i /path/to/key.pem ec2-user@$(terraform output -raw mysql_public_ip)
```

### Verify RHEL version on each VM

```bash
cat /etc/redhat-release
```

Expected output similar to:
```
Red Hat Enterprise Linux release 9.x (Plow)
```

---

## Step 6 — Full Verification Checklist

| Check | Console | CLI |
|---|---|---|
| VPC created | VPC Console → Your VPCs | `aws ec2 describe-vpcs` |
| Subnet created | VPC Console → Subnets | `aws ec2 describe-subnets` |
| Internet Gateway attached | VPC Console → Internet Gateways | `aws ec2 describe-internet-gateways` |
| 3 Security Groups exist | EC2 Console → Security Groups | `aws ec2 describe-security-groups` |
| 3 Instances running | EC2 Console → Instances | `aws ec2 describe-instances` |
| SSH access works | N/A | `ssh -i key.pem ec2-user@<ip>` |
| RHEL confirmed | N/A | `cat /etc/redhat-release` |

---

## Step 7 — Tear Down (Important for Sandbox/Cost Control)

When you are done testing, destroy everything in one command:

```bash
terraform destroy
```

Type `yes` when prompted.

### Verify deletion in Console
1. Open **EC2 Console > Instances** — confirm all 3 show `terminated`.
2. Open **VPC Console > Your VPCs** — confirm `bankdocs-vpc` no longer exists.

### Verify deletion with CLI

```bash
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=bankdocs-frontend,bankdocs-backend,bankdocs-mysql" \
  --query "Reservations[*].Instances[*].State.Name"
```

Should return an empty list or show `terminated` for all.

---

## Full File Structure Recap

```
bankdocs-aws-tf/
├── versions.tf
├── provider.tf
├── variables.tf
├── network.tf
├── security_groups.tf
├── instances.tf
├── outputs.tf
└── terraform.tfvars
```

---

## Command Summary (Copy-Paste Reference)

```bash
# One-time setup
terraform init

# After writing each .tf file
terraform plan
terraform apply

# Check outputs anytime
terraform output

# Full teardown when finished
terraform destroy
```

---

## Interview-Ready Explanation

> I provisioned a 3-tier AWS environment using Terraform: a VPC with a public subnet, three security groups enforcing least-privilege access between tiers (frontend to backend on 8080, backend to MySQL on 3306), and three RHEL 9 EC2 instances. I verified every resource both through the AWS Console and the AWS CLI, and the entire environment is destroyable with a single `terraform destroy` command, which is important for sandbox and cost-controlled environments.

---

## Next Steps After This README

1. Add Ansible or user-data scripts to install nginx, FastAPI, and MySQL automatically on boot.
2. Move the public subnet backend/mysql instances into a private subnet with a NAT gateway for stronger security.
3. Replace the hardcoded RHEL AMI with a `data "aws_ami"` lookup so it always resolves the latest RHEL 9 image per region.
4. Add remote state in S3 with DynamoDB locking once this moves beyond a single-day sandbox.
'''

path = 'output/README.md'
with open(path, 'w') as f:
    f.write(content)

print(len(content), "chars written")