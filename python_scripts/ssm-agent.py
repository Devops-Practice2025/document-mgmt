#!/usr/bin/env python3

import subprocess
import sys
from pathlib import Path


REPO_URL = "https://github.com/Devops-Practice2025/document-mgmt.git"

WORKDIR = "/opt/bankdocs"
FRONTEND_DIR = f"{WORKDIR}/document-mgmt/frontend/bankdocs-ui"
NGINX_ROOT = "/usr/share/nginx/html"


def run(cmd):
    print(f"\n>>> {cmd}")
    result = subprocess.run(
        cmd,
        shell=True,
        text=True
    )

    if result.returncode != 0:
        print(f"FAILED: {cmd}")
        sys.exit(result.returncode)


def install_ssm_agent():
    print("\n=== Installing SSM Agent ===")

    run("""
    sudo dnf install -y \
    https://s3.amazonaws.com/amazon-ssm-us-east-1/latest/linux_amd64/amazon-ssm-agent.rpm
    """)

    run("sudo systemctl enable amazon-ssm-agent")
    run("sudo systemctl restart amazon-ssm-agent")


def install_nginx():
    print("\n=== Installing nginx ===")

    run("sudo dnf install -y nginx")

    run("sudo systemctl enable nginx")
    run("sudo systemctl start nginx")


def install_node():
    print("\n=== Installing Node.js ===")

    run("sudo dnf module disable nodejs -y || true")
    run("sudo dnf module enable nodejs:20 -y")
    run("sudo dnf install -y nodejs")


def clone_repo():
    repo_path = Path(f"{WORKDIR}/document-mgmt")

    if repo_path.exists():
        print("Repository exists. Pulling latest code.")
        run(f"cd {repo_path} && git pull")
    else:
        run(f"sudo mkdir -p {WORKDIR}")
        run(f"sudo chown $USER:$USER {WORKDIR}")
        run(f"cd {WORKDIR} && git clone {REPO_URL}")


def build_frontend():
    print("\n=== Building React App ===")

    run(f"cd {FRONTEND_DIR} && npm install")
    run(f"cd {FRONTEND_DIR} && npm run build")


def deploy_build():
    print("\n=== Deploying React Build ===")

    run(f"sudo rm -rf {NGINX_ROOT}/*")

    run(
        f"sudo cp -r "
        f"{FRONTEND_DIR}/dist/* "
        f"{NGINX_ROOT}/"
    )


def validate_nginx():
    run("sudo nginx -t")
    run("sudo systemctl restart nginx")


def health_check():
    print("\n=== Health Check ===")
    run("curl -I http://localhost")


def main():

    install_ssm_agent()
    install_nginx()
    install_node()

    clone_repo()

    build_frontend()
    deploy_build()

    validate_nginx()
    health_check()

    print("\nDEPLOYMENT SUCCESSFUL")


if __name__ == "__main__":
    main()