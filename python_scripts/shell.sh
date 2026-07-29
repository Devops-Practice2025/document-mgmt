#!/usr/bin/env bash

# Exit immediately when:
# - a command fails                (-e)
# - an undefined variable is used  (-u)
# - a command in a pipeline fails  (pipefail)
set -Eeuo pipefail

#######################################
# Configuration
#######################################

REPO_URL="${REPO_URL:-https://github.com/Devops-Practice2025/document-mgmt.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"

APP_ROOT="${APP_ROOT:-/opt/bankdocs}"
REPO_DIR="${APP_ROOT}/document-mgmt"
FRONTEND_DIR="${REPO_DIR}/frontend/bankdocs-ui"

NGINX_ROOT="${NGINX_ROOT:-/usr/share/nginx/html}"
NGINX_CONFIG="/etc/nginx/conf.d/bankdocs.conf"

# Supply the backend private IP or private DNS name at execution time.
# Do not hardcode an address that may change.
BACKEND_HOST="${BACKEND_HOST:-}"
BACKEND_PORT="${BACKEND_PORT:-8000}"

AWS_REGION="${AWS_REGION:-us-east-1}"

DEPLOY_USER="${SUDO_USER:-ec2-user}"
LOG_FILE="/var/log/bankdocs-frontend-deployment.log"

#######################################
# Logging and error handling
#######################################

log() {
    local level="$1"
    shift

    printf '%s [%s] %s\n' \
        "$(date '+%Y-%m-%d %H:%M:%S')" \
        "${level}" \
        "$*" | tee -a "${LOG_FILE}"
}

die() {
    log "ERROR" "$*"
    exit 1
}

on_error() {
    local exit_code=$?
    local line_number=$1

    log "ERROR" \
        "Deployment failed at line ${line_number}; exit code ${exit_code}."

    log "ERROR" \
        "Review ${LOG_FILE} and the relevant systemd journal."

    exit "${exit_code}"
}

trap 'on_error ${LINENO}' ERR

#######################################
# Preflight validation
#######################################

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        die "Run this script with sudo or as root."
    fi
}

validate_configuration() {
    if [[ -z "${BACKEND_HOST}" ]]; then
        die "BACKEND_HOST is required. Supply the backend private IP or DNS name."
    fi

    if ! [[ "${BACKEND_PORT}" =~ ^[0-9]+$ ]]; then
        die "BACKEND_PORT must be numeric."
    fi

    if ! id "${DEPLOY_USER}" >/dev/null 2>&1; then
        die "Deployment user ${DEPLOY_USER} does not exist."
    fi

    log "INFO" "Repository: ${REPO_URL}"
    log "INFO" "Branch: ${REPO_BRANCH}"
    log "INFO" "Deployment user: ${DEPLOY_USER}"
    log "INFO" "Backend target: ${BACKEND_HOST}:${BACKEND_PORT}"
}

#######################################
# Package and service functions
#######################################

install_base_packages() {
    log "INFO" "Installing base packages."

    dnf install -y \
        git \
        curl \
        nginx \
        policycoreutils-python-utils

    systemctl enable nginx
}

install_nodejs() {
    log "INFO" "Installing Node.js and npm."

    # Try the RHEL Node.js 20 module first.
    if dnf module list nodejs --enabled 2>/dev/null | grep -q '20'; then
        log "INFO" "Node.js 20 module is already enabled."
    else
        dnf module reset nodejs -y || true

        if ! dnf module enable nodejs:20 -y; then
            log "WARN" \
                "Node.js 20 module is unavailable; using the default RHEL package."
        fi
    fi

    dnf install -y nodejs npm

    log "INFO" "Node version: $(node --version)"
    log "INFO" "npm version: $(npm --version)"
}

install_ssm_agent() {
    log "INFO" "Installing AWS Systems Manager Agent."

    if rpm -q amazon-ssm-agent >/dev/null 2>&1; then
        log "INFO" "amazon-ssm-agent is already installed."
    else
        local rpm_url

        rpm_url="https://s3.${AWS_REGION}.amazonaws.com/amazon-ssm-${AWS_REGION}/latest/linux_amd64/amazon-ssm-agent.rpm"

        dnf install -y "${rpm_url}"
    fi

    systemctl enable --now amazon-ssm-agent

    if systemctl is-active --quiet amazon-ssm-agent; then
        log "INFO" "amazon-ssm-agent is active."
    else
        die "amazon-ssm-agent did not start successfully."
    fi
}

#######################################
# Source-code functions
#######################################

prepare_directories() {
    log "INFO" "Preparing application directories."

    mkdir -p "${APP_ROOT}"
    chown "${DEPLOY_USER}:${DEPLOY_USER}" "${APP_ROOT}"
}

synchronize_repository() {
    log "INFO" "Synchronizing the BankDocs repository."

    if [[ -d "${REPO_DIR}/.git" ]]; then
        log "INFO" "Repository already exists; updating it."

        runuser -u "${DEPLOY_USER}" -- \
            git -C "${REPO_DIR}" fetch origin "${REPO_BRANCH}"

        runuser -u "${DEPLOY_USER}" -- \
            git -C "${REPO_DIR}" checkout "${REPO_BRANCH}"

        runuser -u "${DEPLOY_USER}" -- \
            git -C "${REPO_DIR}" reset --hard "origin/${REPO_BRANCH}"
    else
        log "INFO" "Cloning repository for the first deployment."

        runuser -u "${DEPLOY_USER}" -- \
            git clone \
                --branch "${REPO_BRANCH}" \
                --single-branch \
                "${REPO_URL}" \
                "${REPO_DIR}"
    fi

    [[ -d "${FRONTEND_DIR}" ]] ||
        die "Frontend directory does not exist: ${FRONTEND_DIR}"

    [[ -f "${FRONTEND_DIR}/package.json" ]] ||
        die "package.json was not found in ${FRONTEND_DIR}"
}

#######################################
# Build and deployment functions
#######################################

build_frontend() {
    log "INFO" "Installing dependencies and building the React application."

    pushd "${FRONTEND_DIR}" >/dev/null

    # npm ci is deterministic and uses package-lock.json.
    # Fall back to npm install if no lock file exists.
    if [[ -f package-lock.json ]]; then
        runuser -u "${DEPLOY_USER}" -- npm ci
    else
        log "WARN" "package-lock.json not found; using npm install."
        runuser -u "${DEPLOY_USER}" -- npm install
    fi

    runuser -u "${DEPLOY_USER}" -- npm run build

    popd >/dev/null
}

detect_build_directory() {
    if [[ -f "${FRONTEND_DIR}/dist/index.html" ]]; then
        printf '%s\n' "${FRONTEND_DIR}/dist"
    elif [[ -f "${FRONTEND_DIR}/build/index.html" ]]; then
        printf '%s\n' "${FRONTEND_DIR}/build"
    else
        return 1
    fi
}

deploy_frontend_artifact() {
    local build_dir
    local staging_dir
    local backup_dir

    build_dir="$(detect_build_directory)" ||
        die "Could not find dist/index.html or build/index.html."

    staging_dir="${APP_ROOT}/frontend-staging"
    backup_dir="${APP_ROOT}/frontend-backup"

    log "INFO" "Build output detected at ${build_dir}."
    log "INFO" "Staging the new frontend artifact."

    rm -rf "${staging_dir}"
    mkdir -p "${staging_dir}"

    cp -a "${build_dir}/." "${staging_dir}/"

    [[ -f "${staging_dir}/index.html" ]] ||
        die "Staged frontend does not contain index.html."

    log "INFO" "Backing up the current nginx content."

    rm -rf "${backup_dir}"
    mkdir -p "${backup_dir}"

    if [[ -d "${NGINX_ROOT}" ]]; then
        cp -a "${NGINX_ROOT}/." "${backup_dir}/" 2>/dev/null || true
    fi

    log "INFO" "Deploying the new artifact to ${NGINX_ROOT}."

    mkdir -p "${NGINX_ROOT}"
    find "${NGINX_ROOT}" -mindepth 1 -maxdepth 1 -exec rm -rf {} +

    cp -a "${staging_dir}/." "${NGINX_ROOT}/"

    chown -R root:root "${NGINX_ROOT}"
    find "${NGINX_ROOT}" -type d -exec chmod 0755 {} \;
    find "${NGINX_ROOT}" -type f -exec chmod 0644 {} \;

    restorecon -RF "${NGINX_ROOT}" || true
}

#######################################
# nginx, SELinux and firewall
#######################################

configure_nginx() {
    log "INFO" "Creating BankDocs nginx configuration."

    cat >"${NGINX_CONFIG}" <<EOF
server {
    listen 80;
    listen [::]:80;

    server_name _;

    root ${NGINX_ROOT};
    index index.html;

    access_log /var/log/nginx/bankdocs-access.log;
    error_log  /var/log/nginx/bankdocs-error.log;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://${BACKEND_HOST}:${BACKEND_PORT}/;

        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        proxy_connect_timeout 5s;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
    }
}
EOF

    chmod 0644 "${NGINX_CONFIG}"

    # RHEL SELinux blocks nginx outbound network connections unless
    # this boolean is enabled.
    setsebool -P httpd_can_network_connect 1

    restorecon -v "${NGINX_CONFIG}" || true
}

configure_firewall() {
    if ! systemctl is-active --quiet firewalld; then
        log "INFO" "firewalld is not active; no host firewall change required."
        return
    fi

    log "INFO" "Allowing HTTP through firewalld."

    firewall-cmd --permanent --add-service=http
    firewall-cmd --reload
}

validate_and_reload_nginx() {
    log "INFO" "Validating nginx configuration."

    nginx -t

    log "INFO" "Starting or reloading nginx."

    if systemctl is-active --quiet nginx; then
        systemctl reload nginx
    else
        systemctl start nginx
    fi

    systemctl is-active --quiet nginx ||
        die "nginx is not active after deployment."
}

#######################################
# Verification
#######################################

verify_local_frontend() {
    log "INFO" "Checking the local frontend endpoint."

    curl \
        --fail \
        --silent \
        --show-error \
        --retry 5 \
        --retry-delay 2 \
        --output /dev/null \
        http://127.0.0.1/

    log "INFO" "Frontend health check passed."
}

verify_backend_connectivity() {
    log "INFO" "Checking connectivity to the backend port."

    if timeout 5 bash -c \
        "cat < /dev/null > /dev/tcp/${BACKEND_HOST}/${BACKEND_PORT}"
    then
        log "INFO" \
            "Backend ${BACKEND_HOST}:${BACKEND_PORT} is reachable."
    else
        log "WARN" \
            "Backend ${BACKEND_HOST}:${BACKEND_PORT} is not reachable."
        log "WARN" \
            "Check the backend service and security-group rule from the frontend SG."
    fi
}

display_summary() {
    log "INFO" "Deployment completed successfully."
    log "INFO" "Frontend document root: ${NGINX_ROOT}"
    log "INFO" "nginx configuration: ${NGINX_CONFIG}"
    log "INFO" "Deployment log: ${LOG_FILE}"
    log "INFO" "SSM Agent state: $(systemctl is-active amazon-ssm-agent)"
    log "INFO" "nginx state: $(systemctl is-active nginx)"
}

#######################################
# Main workflow
#######################################

main() {
    touch "${LOG_FILE}"
    chmod 0600 "${LOG_FILE}"

    log "INFO" "Starting BankDocs frontend deployment."

    require_root
    validate_configuration

    install_base_packages
    install_nodejs
    install_ssm_agent

    prepare_directories
    synchronize_repository
    build_frontend
    deploy_frontend_artifact

    configure_nginx
    configure_firewall
    validate_and_reload_nginx

    verify_local_frontend
    verify_backend_connectivity
    display_summary
}

main "$@"