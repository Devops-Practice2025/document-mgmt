## Phase 2 Plan — Cloud Deployment

We'll build Phase 2 in this exact order:

```
Step 1: Dockerize backend + frontend
Step 2: Push images to AWS ECR
Step 3: Terraform — VPC, RDS, S3, EKS
Step 4: Deploy to EKS with Kubernetes manifests
Step 5: GitHub Actions CI/CD pipeline
```

Start with the simplest thing first — **Docker**.

***

## Step 1 — Dockerfile for Backend

Create `backend/Dockerfile`:

```dockerfile
# Use official Python 3.11 slim image as base
# "slim" = smaller image, no unnecessary packages
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements first (Docker caches this layer)
# If requirements don't change, Docker won't reinstall packages on rebuild
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend code
COPY . .

# Expose port 8000 so other containers/services can reach it
EXPOSE 8000

# Command to start FastAPI when container runs
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

***

## Step 2 — Dockerfile for Frontend

Create `frontend/bankdocs-ui/Dockerfile`:

```dockerfile
# Stage 1: BUILD
# Use Node to build the React app into static files
FROM node:18-alpine AS build

WORKDIR /app

# Copy package files first (layer caching)
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build React app → creates /app/dist folder with HTML/CSS/JS
RUN npm run build

# Stage 2: SERVE
# Use lightweight nginx to serve the built static files
# nginx image is only ~25MB vs Node which is ~300MB
FROM nginx:alpine

# Copy built files from Stage 1 into nginx's web root
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx config (handles React Router)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

Create `frontend/bankdocs-ui/nginx.conf`:

```nginx
server {
    listen 80;

    location / {
        root /usr/share/nginx/html;
        index index.html;
        # This makes React Router work — all routes serve index.html
        try_files $uri $uri/ /index.html;
    }

    # Forward /api calls to backend service
    location /api {
        proxy_pass http://backend-service:8000;
    }
}
```

***

## Step 3 — Docker Compose (updated for full stack)

Update `docker/docker-compose.yml`:

```yaml
version: "3.8"

services:

  # MySQL Database
  db:
    image: mysql:8
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_DATABASE: bankdocs
      MYSQL_USER: bankdocs
      MYSQL_PASSWORD: bankdocs
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql   # persist data between restarts
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

  # FastAPI Backend
  backend:
    build:
      context: ../backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    env_file:
      - ../backend/.env            # reads your .env file
    depends_on:
      db:
        condition: service_healthy  # waits for MySQL to be ready
    environment:
      DB_HOST: db                   # "db" = the service name above, not localhost

  # React Frontend
  frontend:
    build:
      context: ../frontend/bankdocs-ui
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  mysql_data:
```

***

## Step 4 — Test Docker build locally

```bash
cd /mnt/c/Users/UO85HU/Documents/New_repos/document-mgmt/docker

# Build and start all 3 containers
docker compose up --build

# In a separate terminal, verify all containers are running
docker ps
```

You should see 3 containers: `db`, `backend`, `frontend`.

Open **http://localhost** (port 80) — the React app served by nginx.

***

## One important fix in backend `.env`

When running in Docker, `DB_HOST` must be `db` (the service name), not `localhost`:

```bash
# In backend/.env change:
DB_HOST=db
```

When running locally with `uvicorn` directly, change it back to `localhost`. Or better — use an environment variable that Docker Compose overrides automatically (which the compose file above already does).

***

## What to do right now

```bash
# 1. Create backend/Dockerfile
# 2. Create frontend/bankdocs-ui/Dockerfile
# 3. Create frontend/bankdocs-ui/nginx.conf
# 4. Update docker/docker-compose.yml
# 5. Then run:
cd docker
docker compose up --build
```

Tell me what you see — once Docker is working locally, we move to **ECR + Terraform**. 🚀