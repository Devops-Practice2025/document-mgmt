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