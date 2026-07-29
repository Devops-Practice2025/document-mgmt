#!/usr/bin/env python3

"""
BankDocs frontend deployment script for RHEL 9.

Responsibilities:
- Validate required inputs and privileges
- Install nginx, Git, curl, Node.js and SELinux tools
- Install and start AWS SSM Agent
- Clone or update the BankDocs repository
- Build the React frontend
- Stage, back up and deploy static files
- Configure nginx as a static server and /api reverse proxy
- Configure SELinux and firewalld
- Validate nginx and run health checks
"""

from __future__ import annotations

import argparse
import logging
import os
import pwd
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Sequence


DEFAULT_REPO_URL = (
    "https://github.com/Devops-Practice2025/document-mgmt.git"
)
DEFAULT_BRANCH = "main"
DEFAULT_APP_ROOT = Path("/opt/bankdocs")
DEFAULT_NGINX_ROOT = Path("/usr/share/nginx/html")
DEFAULT_NGINX_CONFIG = Path("/etc/nginx/conf.d/bankdocs.conf")
DEFAULT_LOG_FILE = Path("/var/log/bankdocs-frontend-deployment.log")

SSM_AGENT_RPM_X86_64 = (
    "https://s3.amazonaws.com/"
    "ec2-downloads-windows/SSMAgent/latest/"
    "linux_amd64/amazon-ssm-agent.rpm"
)


class DeploymentError(RuntimeError):
    """Raised when a deployment operation cannot be completed."""


def configure_logging(log_file: Path) -> logging.Logger:
    """
    Configure console and file logging.

    Logs are written to:
    - the terminal
    - /var/log/bankdocs-frontend-deployment.log
    """

    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.touch(exist_ok=True)
    os.chmod(log_file, 0o600)

    logger = logging.getLogger("bankdocs-deployment")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def run_command(
    command: Sequence[str],
    logger: logging.Logger,
    *,
    cwd: Path | None = None,
    user: str | None = None,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess """ Execute a Linux command safely.
    The command must be passed as a list rather than a shell string.
    This avoids unnecessary shell expansion and quoting problems. """

    final_command = list(command)

    if user:
        final_command = [
            "runuser",
            "-u",
            user,
            "--",
            *final_command,
        ]

    logger.info("Running: %s", " ".join(final_command))

    result = subprocess.run(
        final_command,
        cwd=str(cwd) if cwd else None,
        text=True,
        check=False,
        capture_output=capture_output,
    )

    if capture_output:
        if result.stdout:
            logger.info("stdout: %s", result.stdout.strip())

        if result.stderr:
            logger.warning("stderr: %s", result.stderr.strip())

    if check and result.returncode != 0:
        raise DeploymentError(
            f"Command failed with exit code {result.returncode}: "
            f"{' '.join(final_command)}"
        )

    return result


def command_exists(command: str) -> bool:
    """Return True if a command exists in PATH."""

    return shutil.which(command) is not None


def require_root() -> None:
    """Require root because package, systemd and nginx changes need it."""

    if os.geteuid() != 0:
        raise DeploymentError(
            "Run this script using sudo or as the root user."
        )


def validate_user(username: str) -> None:
    """Verify that the non-root deployment user exists."""

    try:
        pwd.getpwnam(username)
    except KeyError as error:
        raise DeploymentError(
            f"Deployment user does not exist: {username}"
        ) from error


def install_base_packages(logger: logging.Logger) -> None:
    """Install packages needed by the application deployment."""

    logger.info("Installing base packages.")

    run_command(
        [
            "dnf",
            "install",
            "-y",
            "git",
            "curl",
            "nginx",
            "python3",
            "policycoreutils-python-utils",
        ],
        logger,
    )

    run_command(
        ["systemctl", "enable", "nginx"],
        logger,
    )


def install_nodejs(logger: logging.Logger) -> None:
    """
    Install Node.js.

    First try to enable the RHEL Node.js 20 module. If that module is
    unavailable, use the default nodejs package from the configured repos.
    """

    logger.info("Installing Node.js and npm.")

    run_command(
        ["dnf", "module", "reset", "nodejs", "-y"],
        logger,
        check=False,
    )

    module_result = run_command(
        ["dnf", "module", "enable", "nodejs:20", "-y"],
        logger,
        check=False,
        capture_output=True,
    )

    if module_result.returncode != 0:
        logger.warning(
            "Node.js 20 module could not be enabled. "
            "Using the default RHEL Node.js package."
        )

    run_command(
        ["dnf", "install", "-y", "nodejs", "npm"],
        logger,
    )

    node_version = run_command(
        ["node", "--version"],
        logger,
        capture_output=True,
    )

    npm_version = run_command(
        ["npm", "--version"],
        logger,
        capture_output=True,
    )

    logger.info("Node version: %s", node_version.stdout.strip())
    logger.info("npm version: %s", npm_version.stdout.strip())


def rpm_is_installed(package_name: str) -> bool:
    """Check whether an RPM package is already installed."""

    result = subprocess.run(
        ["rpm", "-q", package_name],
        text=True,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    return result.returncode == 0


def install_ssm_agent(logger: logging.Logger) -> None:
    """Install, enable, start and verify AWS SSM Agent."""

    logger.info("Checking AWS Systems Manager Agent.")

    if rpm_is_installed("amazon-ssm-agent"):
        logger.info("amazon-ssm-agent is already installed.")
    else:
        logger.info("Installing amazon-ssm-agent.")

        run_command(
            [
                "dnf",
                "install",
                "-y",
                SSM_AGENT_RPM_X86_64,
            ],
            logger,
        )

    run_command(
        [
            "systemctl",
            "enable",
            "--now",
            "amazon-ssm-agent",
        ],
        logger,
    )

    result = run_command(
        [
            "systemctl",
            "is-active",
            "amazon-ssm-agent",
        ],
        logger,
        check=False,
        capture_output=True,
    )

    if result.stdout.strip() != "active":
        raise DeploymentError(
            "amazon-ssm-agent is installed but not active."
        )

    logger.info("amazon-ssm-agent is active.")


def prepare_directories(
    app_root: Path,
    deployment_user: str,
    logger: logging.Logger,
) -> None:
    """Create the application directory and assign it to the deployment user."""

    logger.info("Preparing application directory: %s", app_root)

    app_root.mkdir(parents=True, exist_ok=True)

    user_details = pwd.getpwnam(deployment_user)

    os.chown(
        app_root,
        user_details.pw_uid,
        user_details.pw_gid,
    )


def synchronize_repository(
    repo_url: str,
    branch: str,
    repo_dir: Path,
    deployment_user: str,
    logger: logging.Logger,
) -> None:
    """
    Clone the repository for the first deployment.

    For later deployments:
    - fetch the remote branch
    - check out that branch
    - reset the local working copy to the remote commit
    """

    git_directory = repo_dir / ".git"

    if git_directory.is_dir():
        logger.info("Repository exists. Updating it.")

        run_command(
            ["git", "fetch", "origin", branch],
            logger,
            cwd=repo_dir,
            user=deployment_user,
        )

        run_command(
            ["git", "checkout", branch],
            logger,
            cwd=repo_dir,
            user=deployment_user,
        )

        run_command(
            ["git", "reset", "--hard", f"origin/{branch}"],
            logger,
            cwd=repo_dir,
            user=deployment_user,
        )
    else:
        logger.info("Cloning repository.")

        run_command(
            [
                "git",
                "clone",
                "--branch",
                branch,
                "--single-branch",
                repo_url,
                str(repo_dir),
            ],
            logger,
            user=deployment_user,
        )


def validate_frontend_directory(frontend_dir: Path) -> None:
    """Confirm that the expected frontend project exists."""

    if not frontend_dir.is_dir():
        raise DeploymentError(
            f"Frontend directory does not exist: {frontend_dir}"
        )

    package_file = frontend_dir / "package.json"

    if not package_file.is_file():
        raise DeploymentError(
            f"package.json does not exist: {package_file}"
        )


def build_frontend(
    frontend_dir: Path,
    deployment_user: str,
    logger: logging.Logger,
) -> None:
    """
    Install dependencies and create the production frontend artifact.

    npm ci is preferred when package-lock.json is present because it
    provides a more reproducible installation.
    """

    logger.info("Building the React frontend.")

    package_lock = frontend_dir / "package-lock.json"

    if package_lock.is_file():
        run_command(
            ["npm", "ci"],
            logger,
            cwd=frontend_dir,
            user=deployment_user,
        )
    else:
        logger.warning(
            "package-lock.json was not found. Using npm install."
        )

        run_command(
            ["npm", "install"],
            logger,
            cwd=frontend_dir,
            user=deployment_user,
        )

    run_command(
        ["npm", "run", "build"],
        logger,
        cwd=frontend_dir,
        user=deployment_user,
    )


def detect_build_directory(frontend_dir: Path) -> Path:
    """
    Support both common React output patterns:
    - Vite: dist/
    - Create React App: build/
    """

    candidates = [
        frontend_dir / "dist",
        frontend_dir / "build",
    ]

    for candidate in candidates:
        if (candidate / "index.html").is_file():
            return candidate

    raise DeploymentError(
        "Frontend build failed validation. "
        "Neither dist/index.html nor build/index.html exists."
    )


def clear_directory(directory: Path) -> None:
    """Delete everything inside a directory, but keep the directory itself."""

    directory.mkdir(parents=True, exist_ok=True)

    for item in directory.iterdir():
        if item.is_dir() and not item.is_symlink():
            shutil.rmtree(item)
        else:
            item.unlink()


def copy_directory_contents(source: Path, destination: Path) -> None:
    """Copy source directory contents to destination."""

    destination.mkdir(parents=True, exist_ok=True)

    for item in source.iterdir():
        target = destination / item.name

        if item.is_dir():
            shutil.copytree(
                item,
                target,
                dirs_exist_ok=True,
            )
        else:
            shutil.copy2(item, target)


def deploy_frontend_artifact(
    build_dir: Path,
    app_root: Path,
    nginx_root: Path,
    logger: logging.Logger,
) -> Path:
    """
    Stage the new artifact, back up the current site and deploy.

    Returns the backup directory path.
    """

    staging_dir = app_root / "frontend-staging"
    backup_dir = app_root / "frontend-backup"

    logger.info("Staging build from %s", build_dir)

    clear_directory(staging_dir)
    copy_directory_contents(build_dir, staging_dir)

    if not (staging_dir / "index.html").is_file():
        raise DeploymentError(
            "The staged artifact does not contain index.html."
        )

    logger.info("Backing up current nginx content.")

    clear_directory(backup_dir)

    if nginx_root.is_dir():
        copy_directory_contents(nginx_root, backup_dir)

    logger.info("Deploying frontend artifact to %s", nginx_root)

    clear_directory(nginx_root)
    copy_directory_contents(staging_dir, nginx_root)

    for directory in nginx_root.rglob("*"):
        if directory.is_dir():
            directory.chmod(0o755)
        else:
            directory.chmod(0o644)

        os.chown(directory, 0, 0)

    os.chown(nginx_root, 0, 0)
    nginx_root.chmod(0o755)

    run_command(
        ["restorecon", "-RF", str(nginx_root)],
        logger,
        check=False,
    )

    return backup_dir


def create_nginx_configuration(
    nginx_root: Path,
    nginx_config: Path,
    backend_host: str,
    backend_port: int,
    logger: logging.Logger,
) -> None:
    """Create the BankDocs nginx virtual-host configuration."""

    logger.info("Writing nginx configuration: %s", nginx_config)

    nginx_configuration = f"""server {{
    listen 80;
    listen [::]:80;

    server_name _;

    root {nginx_root};
    index index.html;

    access_log /var/log/nginx/bankdocs-access.log;
    error_log /var/log/nginx/bankdocs-error.log;

    location / {{
        try_files $uri $uri/ /index.html;
    }}

    location /api/ {{
        proxy_pass http://{backend_host}:{backend_port}/;

        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 5s;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
    }}
}}
"""

    nginx_config.parent.mkdir(parents=True, exist_ok=True)
    nginx_config.write_text(
        nginx_configuration,
        encoding="utf-8",
    )
    nginx_config.chmod(0o644)

    run_command(
        ["restorecon", "-v", str(nginx_config)],
        logger,
        check=False,
    )


def configure_selinux(logger: logging.Logger) -> None:
    """
    Allow nginx to connect to the backend application.

    This is needed when SELinux is enforcing and nginx acts as a
    reverse proxy.
    """

    logger.info(
        "Allowing nginx outbound network connections through SELinux."
    )

    run_command(
        [
            "setsebool",
            "-P",
            "httpd_can_network_connect",
            "1",
        ],
        logger,
    )


def configure_firewalld(logger: logging.Logger) -> None:
    """Open HTTP in firewalld if firewalld is currently active."""

    status = run_command(
        ["systemctl", "is-active", "firewalld"],
        logger,
        check=False,
        capture_output=True,
    )

    if status.stdout.strip() != "active":
        logger.info(
            "firewalld is not active. No host firewall change required."
        )
        return

    logger.info("Allowing HTTP through firewalld.")

    run_command(
        [
            "firewall-cmd",
            "--permanent",
            "--add-service=http",
        ],
        logger,
    )

    run_command(
        ["firewall-cmd", "--reload"],
        logger,
    )


def validate_and_reload_nginx(logger: logging.Logger) -> None:
    """Validate nginx before applying the new configuration."""

    logger.info("Validating nginx configuration.")

    run_command(
        ["nginx", "-t"],
        logger,
    )

    status = run_command(
        ["systemctl", "is-active", "nginx"],
        logger,
        check=False,
        capture_output=True,
    )

    if status.stdout.strip() == "active":
        logger.info("Reloading nginx.")

        run_command(
            ["systemctl", "reload", "nginx"],
            logger,
        )
    else:
        logger.info("Starting nginx.")

        run_command(
            ["systemctl", "start", "nginx"],
            logger,
        )

    active_status = run_command(
        ["systemctl", "is-active", "nginx"],
        logger,
        check=False,
        capture_output=True,
    )

    if active_status.stdout.strip() != "active":
        raise DeploymentError(
            "nginx is not active after deployment."
        )


def verify_frontend(logger: logging.Logger) -> None:
    """Check that nginx serves the frontend locally."""

    logger.info("Checking the local frontend endpoint.")

    attempts = 5

    for attempt in range(1, attempts + 1):
        result = run_command(
            [
                "curl",
                "--fail",
                "--silent",
                "--show-error",
                "--output",
                "/dev/null",
                "http://127.0.0.1/",
            ],
            logger,
            check=False,
        )

        if result.returncode == 0:
            logger.info("Frontend health check passed.")
            return

        logger.warning(
            "Frontend health check attempt %s/%s failed.",
            attempt,
            attempts,
        )

        time.sleep(2)

    raise DeploymentError(
        "Frontend health check failed after five attempts."
    )


def verify_backend_connectivity(
    backend_host: str,
    backend_port: int,
    logger: logging.Logger,
) -> None:
    """
    Check whether the frontend VM can establish a TCP connection
    to the backend service.
    """

    if not command_exists("timeout"):
        logger.warning(
            "The timeout command is unavailable. "
            "Skipping backend TCP verification."
        )
        return

    result = run_command(
        [
            "timeout",
            "5",
            "bash",
            "-c",
            (
                f"cat < /dev/null > "
                f"/dev/tcp/{backend_host}/{backend_port}"
            ),
        ],
        logger,
        check=False,
    )

    if result.returncode == 0:
        logger.info(
            "Backend %s:%s is reachable.",
            backend_host,
            backend_port,
        )
    else:
        logger.warning(
            "Backend %s:%s is not reachable. "
            "Check the backend service, listener and security group.",
            backend_host,
            backend_port,
        )


def parse_arguments() -> argparse.Namespace:
    """Read deployment options from command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Deploy the BankDocs React frontend on RHEL 9."
    )

    parser.add_argument(
        "--backend-host",
        required=True,
        help="Backend private IP or internal DNS name.",
    )

    parser.add_argument(
        "--backend-port",
        type=int,
        default=8000,
        help="Backend application port. Default: 8000.",
    )

    parser.add_argument(
        "--repo-url",
        default=DEFAULT_REPO_URL,
        help="BankDocs Git repository URL.",
    )

    parser.add_argument(
        "--branch",
        default=DEFAULT_BRANCH,
        help="Git branch to deploy. Default: main.",
    )

    parser.add_argument(
        "--deployment-user",
        default=os.environ.get("SUDO_USER", "ec2-user"),
        help="Non-root account used for Git and npm.",
    )

    parser.add_argument(
        "--app-root",
        type=Path,
        default=DEFAULT_APP_ROOT,
        help="BankDocs application directory.",
    )

    parser.add_argument(
        "--nginx-root",
        type=Path,
        default=DEFAULT_NGINX_ROOT,
        help="nginx static-content directory.",
    )

    parser.add_argument(
        "--nginx-config",
        type=Path,
        default=DEFAULT_NGINX_CONFIG,
        help="BankDocs nginx configuration file.",
    )

    parser.add_argument(
        "--log-file",
        type=Path,
        default=DEFAULT_LOG_FILE,
        help="Deployment log file.",
    )

    return parser.parse_args()


def main() -> int:
    """Run the complete frontend deployment workflow."""

    arguments = parse_arguments()
    logger: logging.Logger | None = None

    try:
        require_root()
        validate_user(arguments.deployment_user)

        logger = configure_logging(arguments.log_file)

        logger.info("Starting BankDocs frontend deployment.")
        logger.info("Git repository: %s", arguments.repo_url)
        logger.info("Git branch: %s", arguments.branch)
        logger.info(
            "Backend target: %s:%s",
            arguments.backend_host,
            arguments.backend_port,
        )

        repo_dir = arguments.app_root / "document-mgmt"
        frontend_dir = (
            repo_dir / "frontend" / "bankdocs-ui"
        )

        install_base_packages(logger)
        install_nodejs(logger)
        install_ssm_agent(logger)

        prepare_directories(
            arguments.app_root,
            arguments.deployment_user,
            logger,
        )

        synchronize_repository(
            arguments.repo_url,
            arguments.branch,
            repo_dir,
            arguments.deployment_user,
            logger,
        )

        validate_frontend_directory(frontend_dir)

        build_frontend(
            frontend_dir,
            arguments.deployment_user,
            logger,
        )

        build_dir = detect_build_directory(frontend_dir)

        deploy_frontend_artifact(
            build_dir,
            arguments.app_root,
            arguments.nginx_root,
            logger,
        )

        create_nginx_configuration(
            arguments.nginx_root,
            arguments.nginx_config,
            arguments.backend_host,
            arguments.backend_port,
            logger,
        )

        configure_selinux(logger)
        configure_firewalld(logger)
        validate_and_reload_nginx(logger)
        verify_frontend(logger)

        verify_backend_connectivity(
            arguments.backend_host,
            arguments.backend_port,
            logger,
        )

        logger.info("BankDocs frontend deployment succeeded.")
        logger.info(
            "Frontend files: %s",
            arguments.nginx_root,
        )
        logger.info(
            "Deployment log: %s",
            arguments.log_file,
        )

        return 0

    except DeploymentError as error:
        if logger:
            logger.exception("Deployment failed: %s", error)
        else:
            print(
                f"Deployment failed: {error}",
                file=sys.stderr,
            )

        return 1

    except Exception as error:
        if logger:
            logger.exception(
                "Unexpected deployment failure: %s",
                error,
            )
        else:
            print(
                f"Unexpected failure: {error}",
                file=sys.stderr,
            )

        return 2


if __name__ == "__main__":
    sys.exit(main())
