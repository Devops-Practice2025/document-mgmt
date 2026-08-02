Yes — you can do this with only **Terraform + gcloud CLI**. The right flow is: authenticate `gcloud` using your workforce pool, make sure that federated identity has permission in the project, then run Terraform to create 3 Compute Engine VMs. Google documents browser-based `gcloud` sign-in for Workforce Identity Federation using a login config created from `locations/global/workforcePools/.../providers/...`, and Terraform supports Compute Engine VM creation through `google_compute_instance`. [docs.cloud.google](https://docs.cloud.google.com/iam/docs/workforce-log-in-gcloud)

## Login with workforce identity

First create the login config for your workforce pool and provider, then sign in with `gcloud`. Google’s documented flow is:

```bash
gcloud iam workforce-pools create-login-config \
  locations/global/workforcePools/sandbox-p/providers/PROVIDER_ID \
  --output-file=login-config.json
```

Then log in:

```bash
gcloud auth login --login-config=login-config.json
```

You can also activate the file so normal `gcloud auth login` reuses it later. [cloud.google](https://cloud.google.com/sdk/gcloud/reference/iam/workforce-pools/create-login-config)

## Set project and verify access

After login, set the target project and verify your federated identity can access it:

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud auth list
gcloud compute instances list
```

Workforce Identity Federation gives external users access to Google Cloud resources through IAM, so the federated principal must already have sufficient roles on the project. [docs.cloud.google](https://docs.cloud.google.com/iam/docs/workforce-identity-federation)

## Terraform files

Create a folder like this:

```bash
mkdir gcp-3vm
cd gcp-3vm
touch main.tf variables.tf terraform.tfvars
```

### `main.tf`

```hcl
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

resource "google_compute_instance" "frontend" {
  name         = "bankdocs-frontend"
  machine_type = var.machine_type
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "rhel-cloud/rhel-9"
    }
  }

  network_interface {
    network = "default"
    access_config {}
  }

  tags = ["frontend"]
}

resource "google_compute_instance" "backend" {
  name         = "bankdocs-backend"
  machine_type = var.machine_type
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "rhel-cloud/rhel-9"
    }
  }

  network_interface {
    network = "default"
    access_config {}
  }

  tags = ["backend"]
}

resource "google_compute_instance" "mysql" {
  name         = "bankdocs-mysql"
  machine_type = var.machine_type
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "rhel-cloud/rhel-9"
    }
  }

  network_interface {
    network = "default"
    access_config {}
  }

  tags = ["mysql"]
}
```

### `variables.tf`

```hcl
variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "zone" {
  type    = string
  default = "us-central1-a"
}

variable "machine_type" {
  type    = string
  default = "e2-medium"
}
```

### `terraform.tfvars`

```hcl
project_id   = "YOUR_PROJECT_ID"
region       = "us-central1"
zone         = "us-central1-a"
machine_type = "e2-medium"
```

The `google_compute_instance` resource is the standard Terraform resource for managing GCE VM instances, and Google’s Terraform quickstart uses this resource type for VM creation. [docs.cloud.google](https://docs.cloud.google.com/docs/terraform/create-vm-instance)

## Run Terraform

Initialize and apply:

```bash
terraform init
terraform plan
terraform apply
```

This creates exactly 3 VMs: frontend, backend, and mysql. [registry.terraform](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/compute_instance)

## Optional firewall rules

If you want the frontend public and backend/MySQL restricted, add firewall rules too:

```hcl
resource "google_compute_firewall" "frontend_http" {
  name    = "allow-frontend-http"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["frontend"]
}

resource "google_compute_firewall" "backend_api" {
  name    = "allow-backend-8080"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["8080"]
  }

  source_tags = ["frontend"]
  target_tags = ["backend"]
}

resource "google_compute_firewall" "mysql_3306" {
  name    = "allow-mysql-3306"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["3306"]
  }

  source_tags = ["backend"]
  target_tags = ["mysql"]
}
```

## What this gives you

You will have:

- `bankdocs-frontend` VM
- `bankdocs-backend` VM
- `bankdocs-mysql` VM
- RHEL 9 on each VM
- Public IPs by default
- Federated login to GCP through your workforce pool
- Terraform-managed infrastructure state

## One important note

Workforce Identity Federation is for **your login and authorization to Google Cloud**, not something you install inside the VM. The VMs themselves are normal Compute Engine resources created after your federated identity is authenticated and authorized. [docs.cloud.google](https://docs.cloud.google.com/iam/docs/workforce-log-in-gcloud)

## Clean next step

After the VMs are created, the next task is OS/app configuration:

- frontend VM → nginx + React build
- backend VM → Python + FastAPI
- mysql VM → MySQL server

I can give you the **full Terraform project** next, including:
- `outputs.tf`
- firewall rules
- startup scripts
- SSH metadata
- separate private subnet design

Here’s a complete `README.md` you can drop into a GCP Terraform folder to deploy **three RHEL-based VMs (frontend, backend, mysql)**, with step‑by‑step apply and verification via console and `gcloud` CLI. It follows the same structure as the AWS README but uses GCP services and Terraform’s `google_compute_instance` resource, as in Google’s official quickstart. [docs.cloud.google](https://docs.cloud.google.com/docs/terraform/create-vm-instance)

***

```markdown
# BankDocs on GCP: Terraform Step-by-Step for RHEL VMs

## Overview

This README walks through building a simple 3-tier BankDocs lab on **Google Cloud Platform** using **Terraform**, one step at a time.

You will:

- Configure the Google provider.
- Create three Compute Engine VM instances:
  - `bankdocs-frontend`
  - `bankdocs-backend`
  - `bankdocs-mysql`
- Use the **default VPC network** to keep the sandbox simple.
- Verify everything in **GCP Console** and via **`gcloud` CLI**.
- Destroy all resources cleanly at the end with `terraform destroy`.

This mirrors the AWS README structure but stays lightweight for a **one‑day sandbox**.

---

## Prerequisites

### Tools

```bash
# Verify gcloud CLI
gcloud version

# Verify Terraform
terraform -version
```

### GCP setup

Follow Google’s Terraform quickstart flow: [web:115][web:130]

1. **Create or select a project**:

```bash
gcloud projects create YOUR_PROJECT_ID
gcloud config set project YOUR_PROJECT_ID
```

2. **Enable Compute Engine API**:

```bash
gcloud services enable compute.googleapis.com
```

3. **Grant yourself instance admin** (simplified for lab):

```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="user:YOUR_WORK_EMAIL" \
  --role="roles/compute.instanceAdmin.v1"
```

Make sure billing is enabled on the project. [web:115][web:136]

---

## Step 1 — Project Folder and Terraform Skeleton

Create a working folder:

```bash
mkdir -p ~/bankdocs-gcp-tf
cd ~/bankdocs-gcp-tf
```

Create these files:

```bash
touch versions.tf provider.tf variables.tf instances.tf outputs.tf terraform.tfvars
```

Your layout will be:

```text
bankdocs-gcp-tf/
├── versions.tf
├── provider.tf
├── variables.tf
├── instances.tf
├── outputs.tf
└── terraform.tfvars
```

---

## Step 2 — Provider and Versions

### What you're building

Tell Terraform to use the **Google Cloud provider** and require a recent Terraform version. Google’s docs use the `hashicorp/google` provider for GCP resources. [web:115][web:122]

### `versions.tf`

```hcl
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}
```

### `provider.tf`

```hcl
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}
```

### `variables.tf`

```hcl
variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "zone" {
  type    = string
  default = "us-central1-a"
}

variable "machine_type" {
  type    = string
  default = "e2-medium"
}

# RHEL image family in GCP - update if you prefer another OS
variable "rhel_image" {
  type    = string
  default = "rhel-cloud/rhel-9"  # RHEL 9 public image family
}
```

### `terraform.tfvars`

```hcl
project_id   = "YOUR_PROJECT_ID"
region       = "us-central1"
zone         = "us-central1-a"
machine_type = "e2-medium"
```

### Initialize Terraform

```bash
terraform init
```

**Expected output** (similar to Google’s quickstart): [web:115][web:136]

- Provider `hashicorp/google` downloaded.
- “Terraform has been successfully initialized!”

---

## Step 3 — The 3 Compute Engine Instances

### What you're building

Three **Compute Engine VM instances** on the default network:

- `bankdocs-frontend`
- `bankdocs-backend`
- `bankdocs-mysql`

Google’s quickstart uses `google_compute_instance` for a single VM; here we use the same resource type but define three resources. [web:115][web:116][web:136]

### `instances.tf`

```hcl
resource "google_compute_instance" "frontend" {
  name         = "bankdocs-frontend"
  machine_type = var.machine_type
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = var.rhel_image
    }
  }

  # Use default VPC network for sandbox simplicity
  network_interface {
    network       = "default"
    access_config {}  # creates an ephemeral public IP
  }

  tags = ["frontend"]
}

resource "google_compute_instance" "backend" {
  name         = "bankdocs-backend"
  machine_type = var.machine_type
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = var.rhel_image
    }
  }

  network_interface {
    network       = "default"
    access_config {}
  }

  tags = ["backend"]
}

resource "google_compute_instance" "mysql" {
  name         = "bankdocs-mysql"
  machine_type = var.machine_type
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = var.rhel_image
    }
  }

  network_interface {
    network       = "default"
    access_config {}
  }

  tags = ["mysql"]
}
```

The `google_compute_instance` resource is exactly the same type used in Google’s official quickstart, where they create a single VM named `my-vm`. [web:115][web:116][web:136]

---

## Step 4 — Outputs (IP Addresses)

### `outputs.tf`

```hcl
output "frontend_public_ip" {
  value = google_compute_instance.frontend.network_interface.access_config.nat_ip
}

output "backend_public_ip" {
  value = google_compute_instance.backend.network_interface.access_config.nat_ip
}

output "mysql_public_ip" {
  value = google_compute_instance.mysql.network_interface.access_config.nat_ip
}
```

These outputs make it easy to SSH into each VM without manually copy‑pasting IPs from the console.

---

## Step 5 — Plan and Apply

### Plan

```bash
terraform plan
```

**Expected output** (similar pattern to Google’s quickstart): [web:115][web:136]

- “Plan: 3 to add, 0 to change, 0 to destroy.”

### Apply

```bash
terraform apply
```

When prompted, type `yes`.

**Expected output:**

- “Apply complete! Resources: 3 added, 0 changed, 0 destroyed.”

Then:

```bash
terraform output
```

You should see:

```text
backend_public_ip  = "x.x.x.x"
frontend_public_ip = "x.x.x.x"
mysql_public_ip    = "x.x.x.x"
```

---

## Step 6 — Verify in GCP Console

### Instances

1. Open **Compute Engine → VM instances** in the GCP Console.
2. Confirm you see:
   - `bankdocs-frontend`
   - `bankdocs-backend`
   - `bankdocs-mysql`
3. Click each instance:
   - Check **Zone** matches `us-central1-a`.
   - Check **Machine type** shows `e2-medium` (or what you set).
   - Check **Boot disk** uses a RHEL image (e.g. `rhel-9`). [web:141]

---

## Step 7 — Verify with `gcloud` CLI

From your terminal (Cloud Shell or local with SDK installed):

```bash
gcloud compute instances list \
  --filter="name=('bankdocs-frontend','bankdocs-backend','bankdocs-mysql')" \
  --format="table(name,zone,status,EXTERNAL_IP)"
```

You should see a table with 3 RUNNING instances and their external IPs. `gcloud compute instances create` is the manual CLI way to create VMs; here, Terraform is calling the same APIs for you. [web:139][web:115]

---

## Step 8 — SSH In and Confirm RHEL

Use the outputs to SSH:

```bash
# Frontend
gcloud compute ssh bankdocs-frontend --zone="${TF_VAR_zone:-us-central1-a}"

# Or via IP:
ssh ec2-user@$(terraform output -raw frontend_public_ip)
# On GCP RHEL, default user may be `ec2-user` or `rhel` depending on image;
# check the image docs if login fails.

# Backend
gcloud compute ssh bankdocs-backend --zone="${TF_VAR_zone:-us-central1-a}"

# MySQL
gcloud compute ssh bankdocs-mysql --zone="${TF_VAR_zone:-us-central1-a}"
```

Inside each VM:

```bash
cat /etc/redhat-release
```

You should see a RHEL 9 release string (exact text can vary slightly by minor version).

---

## Step 9 — Clean Up (Important for Sandbox / Cost Control)

When you are done with the sandbox, destroy everything:

```bash
terraform destroy
```

Type `yes` when prompted.

Terraform’s destroy command is documented as the inverse of apply: it calls the Google Cloud APIs to remove the resources defined in your configuration. [web:121][web:122]

### Verify deletion in Console

1. Open **Compute Engine → VM instances**.
2. Confirm the three VMs are gone (or in `TERMINATED` state if you keep history).

### Verify with CLI

```bash
gcloud compute instances list \
  --filter="name=('bankdocs-frontend','bankdocs-backend','bankdocs-mysql')"
```

Should return no rows.

---

## Command Summary (Copy-Paste Reference)

```bash
# One-time setup
terraform init

# After writing/adjusting .tf files
terraform plan
terraform apply

# Check outputs
terraform output

# Full teardown
terraform destroy
```

---

## Interview-Ready Explanation

> I provisioned a 3-tier lab on Google Cloud using Terraform. The configuration uses the `hashicorp/google` provider to create three Compute Engine VM instances named `bankdocs-frontend`, `bankdocs-backend`, and `bankdocs-mysql`, all running RHEL on the default VPC network. I validated the plan with `terraform plan`, applied it with `terraform apply`, and verified the instances both in the GCP Console and via `gcloud compute instances list`. The entire environment can be destroyed with a single `terraform destroy` command, which is critical for one-day sandbox and cost-controlled environments. [web:115][web:116][web:130]

---

## Next Steps After This README

1. Add a **VPC + subnet** instead of using the default network, for more realistic isolation.
2. Add **firewall rules** (GCP network tags + `google_compute_firewall`) so only frontend can reach backend, and only backend can reach MySQL.
3. Add **startup scripts** or Ansible to install Nginx/React, FastAPI, and MySQL automatically.
4. Move Terraform state into a **Cloud Storage bucket** if you use this beyond a single-day sandbox. Google’s Terraform docs include a state-in-bucket pattern. [web:130]
```

If you want, I can extend this README to include firewall rules and a custom VPC/subnet (similar to the AWS version) while still keeping it sandbox-friendly.