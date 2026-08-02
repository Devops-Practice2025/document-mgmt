You can recreate the same setup entirely from the **Google Cloud Console**, without Terraform. Think in terms of:

- Project and API
- 3 VM instances (frontend, backend, mysql)
- Optional firewall rules

Below is a clear, click‑by‑click guide that maps closely to what Terraform would do. [docs.cloud.google](https://docs.cloud.google.com/docs/terraform/create-vm-instance)

***

## 1. Prepare project and API

### Create or select a project

1. Go to **https://console.cloud.google.com/**.
2. Top bar → **Project selector** → either:
   - Click **New Project** (give it a name, e.g. `bankdocs-gcp`), or
   - Select your existing sandbox project.

### Enable Compute Engine API

1. In the left navigation, go to **APIs & Services → Library**.
2. Search for **Compute Engine API**.
3. Click it → **Enable**.

Google’s Terraform VM quickstart starts with the same step: a project with Compute Engine enabled. [cloud.google](https://cloud.google.com/docs/terraform/create-vm-instance?hl=ko)

***

## 2. Create the frontend VM (RHEL)

Goal: `bankdocs-frontend` running RHEL, on the default network, with a public IP.

1. In the left menu, go to **Compute Engine → VM instances**.
2. Click **Create instance**.
3. Fill in:
   - **Name**: `bankdocs-frontend`
   - **Region**: `us-central1` (or your choice)
   - **Zone**: `us-central1-a` (match what you plan for Terraform)
4. Under **Machine configuration**:
   - **Series**: `E2` (or N2, etc.)
   - **Machine type**: `e2-medium` (2 vCPU, 4 GB RAM is fine for lab).
5. Under **Boot disk**:
   - Click **Change**.
   - **Operating system**: choose **Red Hat Enterprise Linux**.
   - **Version**: RHEL 9 (or latest available).
   - Confirm **Boot disk type** and size (default 10–20 GB is fine).
   - Click **Select**.
6. Under **Network**:
   - Network: `default` (for simple sandbox; we’re not creating custom VPC here).
   - Subnetwork: default for the region.
   - Leave **External IP** as **Ephemeral** (this gives a public IP).
7. (Optional) Under **Network tags**, add: `frontend`.
8. Leave other fields default for now.
9. Click **Create**.

You now have a RHEL VM similar to the single VM described in Google’s VM creation docs. [cloud.google](https://cloud.google.com/compute/docs/samples/compute-instances-create)

***

## 3. Create the backend VM

Repeat similar steps, changing the name and optionally tags.

1. **Compute Engine → VM instances** → **Create instance**.
2. **Name**: `bankdocs-backend`.
3. **Region/Zone**: same as frontend (e.g. `us-central1/us-central1-a`).
4. **Machine type**: `e2-medium`.
5. **Boot disk**:
   - **OS**: Red Hat Enterprise Linux.
   - **Version**: RHEL 9.
6. **Network**:
   - Network: `default`.
   - External IP: **Ephemeral** (for quick SSH and a simple lab).
7. Network tags: `backend` (optional).
8. Click **Create**.

***

## 4. Create the MySQL VM

1. **Compute Engine → VM instances** → **Create instance**.
2. **Name**: `bankdocs-mysql`.
3. **Region/Zone**: same as others.
4. **Machine type**: `e2-medium` (or a bit larger if you plan heavy DB load).
5. **Boot disk**:
   - OS: Red Hat Enterprise Linux.
   - Version: RHEL 9.
   - Optionally increase disk size (e.g. 50 GB) for a more realistic DB server.
6. **Network**:
   - Network: `default`.
   - External IP: for a real environment you’d usually **disable** public IP here and keep DB private, but for a simple 1‑day sandbox you can leave Ephemeral and tighten firewall rules.
7. Network tags: `mysql` (optional).
8. Click **Create**.

Google’s Compute Engine “Create a VM instance” docs describe the same fields: name, zone, machine type, boot disk, network, and external IP. [cloud.google](https://cloud.google.com/compute/docs/samples/compute-instances-create)

***

## 5. Add firewall rules (optional but recommended)

To mimic the tiered security of your AWS/Terraform design, define simple firewall rules using **network tags**:

### Allow HTTP to frontend

1. Go to **VPC network → Firewall**.
2. Click **Create firewall rule**.
3. Set:
   - **Name**: `allow-frontend-http`.
   - **Network**: `default`.
   - **Targets**: **Specified target tags** → enter `frontend`.
   - **Source filter**: **IP ranges**.
   - **Source IP ranges**: `0.0.0.0/0` (public).
   - **Protocols and ports**:
     - Check **tcp**.
     - Ports: `80,443`.
4. Click **Create**.

### Allow backend API only from frontend

1. **Create firewall rule**.
2. **Name**: `allow-backend-8080`.
3. **Network**: `default`.
4. **Targets**: **Specified target tags** → `backend`.
5. **Source filter**: **Source tags**.
   - Source tags: `frontend`.
6. **Protocols and ports**:
   - tcp → `8080`.
7. Click **Create**.

### Allow MySQL only from backend

1. **Create firewall rule**.
2. **Name**: `allow-mysql-3306`.
3. **Network**: `default`.
4. **Targets**: **Specified target tags** → `mysql`.
5. **Source filter**: **Source tags**.
   - Source tags: `backend`.
6. **Protocols and ports**:
   - tcp → `3306`.
7. Click **Create**.

This uses the same idea as the security-group design you used in AWS: traffic to DB is allowed only from backend, and traffic to backend only from frontend.

***

## 6. Verify via Console and `gcloud` CLI

### Console checks

1. **VMs**
   - Go to **Compute Engine → VM instances**.
   - Confirm:
     - `bankdocs-frontend` (RUNNING).
     - `bankdocs-backend` (RUNNING).
     - `bankdocs-mysql` (RUNNING).
   - Check each instance:
     - Zone: matches your choice.
     - Machine type: e2-medium (or what you picked).
     - Boot disk: RHEL 9 image.
     - Network tags: `frontend`, `backend`, `mysql` (if you set them).

2. **Firewall**
   - Go to **VPC network → Firewall**.
   - Confirm rules:
     - `allow-frontend-http` targets `frontend`.
     - `allow-backend-8080` targets `backend`, source `frontend`.
     - `allow-mysql-3306` targets `mysql`, source `backend`.

### CLI checks (`gcloud`)

List instances:

```bash
gcloud compute instances list \
  --filter="name=('bankdocs-frontend','bankdocs-backend','bankdocs-mysql')" \
  --format="table(name,zone,status,EXTERNAL_IP,tags.list())"
```

This uses the same `gcloud compute instances list` pattern shown in GCP docs for verifying instance creation. [docs.cloud.google](https://docs.cloud.google.com/sdk/gcloud/reference/compute/instances/create)

List firewall rules:

```bash
gcloud compute firewall-rules list \
  --filter="name=('allow-frontend-http','allow-backend-8080','allow-mysql-3306')" \
  --format="table(name,network,targetTags,sourceTags,allowed)"
```

***

## 7. Clean up (important for 1‑day sandbox)

When you are done:

### Delete VMs from console

1. **Compute Engine → VM instances**.
2. Tick the three checkboxes.
3. Click **Delete**.

### Or delete via `gcloud`

```bash
gcloud compute instances delete bankdocs-frontend bankdocs-backend bankdocs-mysql \
  --zone=us-central1-a
```

Google’s VM quickstart recommends cleaning up resources to avoid ongoing charges; same principle here. [developer.hashicorp](https://developer.hashicorp.com/terraform/tutorials/gcp-get-started)

***

If you want, I can now turn this into a dedicated `README.md` for **manual GCP console + `gcloud` steps**, matching the format of your AWS Terraform README but focused purely on manual operations.