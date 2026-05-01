# syntax=docker/dockerfile:1.6
# ---------------------------------------------------------------------------
# Reverse Document Generator — Flask Application Container Image
# ---------------------------------------------------------------------------
# This Dockerfile builds the runtime image for the Reverse Document Generator
# Flask application (archie-job-reverse-document-generator) deployed as a
# Cloud Run **Service** (long-lived HTTP server) — replacing the previous
# Cloud Run **Job** (one-shot batch process) deployment model.
#
# Critical preserved capabilities:
#   * Docker-in-Docker (DinD) — required because the LangGraph pipeline uses
#     ANTHROPIC_BASH_TOOL_DEFINITION for sandboxed code generation. The
#     Docker daemon is started inside this container by /app/start.sh
#     before the application server is launched.
#   * Node.js 22 LTS — required for the Chrome DevTools MCP and Figma MCP
#     tool servers spawned via npx by the Search/Author agents.
#   * Google Chrome — required by the Chrome DevTools MCP server for
#     headless browser automation during context gathering.
#   * Security patches for libpam, gnutls28, and openssh — applied via
#     apt-get install --only-upgrade against the Ubuntu 24.04 base image.
#
# Migration delta vs. the previous Cloud Run Job image:
#   * Final exec line in /app/start.sh changed from `exec python main.py`
#     to `exec gunicorn ... wsgi:app` so that the container hosts a
#     long-lived WSGI server bound to 0.0.0.0:8080 instead of running the
#     pipeline once and exiting.
#   * EXPOSE 8080 added for documentation and local docker-run convenience
#     (Cloud Run ignores EXPOSE for routing but uses $PORT, which is 8080).
# ---------------------------------------------------------------------------
FROM ubuntu:24.04

# ---------------------------------------------------------------------------
# Security patches — apply CVE fixes on top of the base image's package set.
# `--only-upgrade` ensures we update existing packages without installing
# unrelated new ones. These three groups address recurring CVEs flagged by
# container scanners (e.g. Trivy, Grype) on the ubuntu:24.04 base image.
# ---------------------------------------------------------------------------
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --only-upgrade --no-install-recommends \
        libpam-modules \
        libpam-modules-bin \
        libpam-runtime \
        libpam0g \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --only-upgrade --no-install-recommends \
        libgnutls30 \
        libgnutls-dane0 \
        libgnutls-openssl27 \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --only-upgrade --no-install-recommends \
        openssh-client \
        openssh-server \
        openssh-sftp-server \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Base system packages — Python 3.12, build tools, networking utilities,
# process supervision, and FUSE overlay support (needed for DinD overlay2
# storage driver inside an unprivileged container environment).
# ---------------------------------------------------------------------------
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        wget \
        gnupg \
        lsb-release \
        software-properties-common \
        apt-transport-https \
        git \
        unzip \
        zip \
        jq \
        supervisor \
        fuse-overlayfs \
        iptables \
        uidmap \
        kmod \
        xz-utils \
        build-essential \
        pkg-config \
        libffi-dev \
        libssl-dev \
        python3.12 \
        python3.12-venv \
        python3.12-dev \
        python3-pip \
        python-is-python3 \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Node.js 22 LTS — required for `npx` invocation of MCP tool servers
# (Chrome DevTools MCP and Figma MCP) by the LangGraph agents.
# ---------------------------------------------------------------------------
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && node --version \
    && npm --version

# ---------------------------------------------------------------------------
# Upgrade transitive npm dependencies that are flagged by security scanners
# on Node.js 22's bundled npm. We use `npm install -g <pkg>@latest` to
# replace the vulnerable nested versions of `glob`, `brace-expansion`, and
# `diff` in the global npm tree. Each upgrade is run in its own RUN layer
# so a failure in one does not invalidate the others' cache.
# ---------------------------------------------------------------------------
RUN npm install -g glob@latest \
    && npm cache clean --force

RUN npm install -g brace-expansion@latest \
    && npm cache clean --force

RUN npm install -g diff@latest \
    && npm cache clean --force

# ---------------------------------------------------------------------------
# Google Chrome stable — used by the Chrome DevTools MCP server for
# headless browser automation. Installed from Google's official APT repo
# so that updates flow through `apt-get upgrade` like other system packages.
# ---------------------------------------------------------------------------
RUN curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Pin pip to 25.3 and ensure setuptools >= 70.0.0 — these versions contain
# fixes for CVE-2024-6345 (setuptools) and resolver improvements that the
# downstream `pip install -r requirements.txt` step relies on. We use
# --break-system-packages because Ubuntu 24.04 marks /usr/lib/python3.12 as
# externally-managed (PEP 668); this image is single-tenant so the global
# install is acceptable.
# ---------------------------------------------------------------------------
RUN python -m pip install --break-system-packages --upgrade --no-cache-dir \
        pip==25.3

RUN python -m pip install --break-system-packages --upgrade --no-cache-dir \
        "setuptools>=70.0.0" \
        "wheel>=0.45.0"

# ---------------------------------------------------------------------------
# Docker Engine + CLI + containerd — required for Docker-in-Docker. The
# LangGraph pipeline's bash tool (ANTHROPIC_BASH_TOOL_DEFINITION) executes
# generated code inside ephemeral docker containers for isolation.
# ---------------------------------------------------------------------------
RUN install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        docker-ce \
        docker-ce-cli \
        containerd.io \
        docker-buildx-plugin \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---------------------------------------------------------------------------
# Document the HTTP port that Gunicorn binds to. Cloud Run ignores EXPOSE
# for actual routing (it uses $PORT, which we hard-code to 8080 below) but
# this directive makes `docker run -P` and local introspection tools work.
# ---------------------------------------------------------------------------
EXPOSE 8080

# ---------------------------------------------------------------------------
# Runtime environment configuration.
#   * DBUS_SESSION_BUS_ADDRESS=/dev/null prevents Chrome from trying to
#     contact a session D-Bus daemon (none exists in the container).
#   * CHROME_DEVEL_SANDBOX=0 disables Chrome's setuid sandbox; the MCP
#     server runs Chrome with --no-sandbox in this restricted environment.
# ---------------------------------------------------------------------------
ENV DBUS_SESSION_BUS_ADDRESS=/dev/null
ENV CHROME_DEVEL_SANDBOX=0

# ---------------------------------------------------------------------------
# Install the GCP Artifact Registry keyring backend so that the subsequent
# `pip install -r requirements.txt` can fetch the private internal packages
# (blitzy-platform-shared) from us-east1-python.pkg.dev using the mounted
# service-account credentials.
# ---------------------------------------------------------------------------
RUN python -m pip install --break-system-packages --no-cache-dir \
        keyrings.google-artifactregistry-auth

# ---------------------------------------------------------------------------
# Copy only the dependency manifest first so that pip install layer is
# cached when application code changes but dependencies don't.
# ---------------------------------------------------------------------------
COPY requirements.txt .

# ---------------------------------------------------------------------------
# Remove the system-managed python3-jwt apt package — it conflicts with the
# `PyJWT` wheel pulled in transitively by the Python requirements (e.g. via
# google-auth). Removing the dpkg-tracked version lets pip own the install.
# ---------------------------------------------------------------------------
RUN DEBIAN_FRONTEND=noninteractive apt-get remove -y python3-jwt \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Install Python dependencies from requirements.txt. The
# `--mount=type=secret` BuildKit feature exposes the Google service-account
# JSON at build time without baking it into the final image layer. The
# keyrings.google-artifactregistry-auth backend reads
# GOOGLE_APPLICATION_CREDENTIALS to authenticate against the private
# Artifact Registry index declared in requirements.txt.
# ---------------------------------------------------------------------------
RUN --mount=type=secret,id=google_credentials,target=/tmp/google_credentials.json \
    GOOGLE_APPLICATION_CREDENTIALS=/tmp/google_credentials.json \
    python -m pip install --break-system-packages --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# Copy the rest of the application source tree (Flask app/, lib/reverse_document/,
# wsgi.py, run.py, find_trace_runs.py, etc.). The .dockerignore file controls
# what is excluded from this copy.
# ---------------------------------------------------------------------------
COPY . .

# ---------------------------------------------------------------------------
# Generate the container entrypoint script. /app/start.sh:
#   1. Cleans up any stale Docker daemon state from a previous container run.
#   2. Starts the Docker daemon in the background using the overlay2 storage
#      driver (preferred for performance).
#   3. Falls back to the vfs storage driver if overlay2 cannot start (e.g.
#      when the container's filesystem doesn't support overlay mounts).
#   4. Waits for the Docker daemon to become responsive.
#   5. Execs Gunicorn (replacing PID 1's child) so signals from Cloud Run
#      propagate cleanly to the WSGI server.
#
# Note: This RUN intentionally OVERWRITES any /app/start.sh that may have
# been COPY'd in from the build context above — the canonical start.sh is
# always the inline-generated one below.
# ---------------------------------------------------------------------------
RUN echo '#!/bin/bash' > /app/start.sh && \
    echo 'set -e' >> /app/start.sh && \
    echo '' >> /app/start.sh && \
    echo '# ---- Clean up any stale Docker daemon state ----' >> /app/start.sh && \
    echo 'rm -f /var/run/docker.pid' >> /app/start.sh && \
    echo 'rm -f /var/run/docker.sock' >> /app/start.sh && \
    echo '' >> /app/start.sh && \
    echo '# ---- Try overlay2 storage driver first (preferred) ----' >> /app/start.sh && \
    echo 'echo "[start.sh] Starting Docker daemon with overlay2 storage driver..."' >> /app/start.sh && \
    echo 'dockerd --storage-driver=overlay2 > /var/log/dockerd.log 2>&1 &' >> /app/start.sh && \
    echo 'DOCKERD_PID=$!' >> /app/start.sh && \
    echo '' >> /app/start.sh && \
    echo 'WAIT_TIME=10' >> /app/start.sh && \
    echo 'SUCCESS=0' >> /app/start.sh && \
    echo 'for i in $(seq 1 $WAIT_TIME); do' >> /app/start.sh && \
    echo '    if docker info > /dev/null 2>&1; then' >> /app/start.sh && \
    echo '        SUCCESS=1' >> /app/start.sh && \
    echo '        echo "[start.sh] Docker daemon ready (overlay2) after ${i}s"' >> /app/start.sh && \
    echo '        break' >> /app/start.sh && \
    echo '    fi' >> /app/start.sh && \
    echo '    if ! kill -0 $DOCKERD_PID 2>/dev/null; then' >> /app/start.sh && \
    echo '        echo "[start.sh] dockerd (overlay2) exited prematurely"' >> /app/start.sh && \
    echo '        break' >> /app/start.sh && \
    echo '    fi' >> /app/start.sh && \
    echo '    sleep 1' >> /app/start.sh && \
    echo 'done' >> /app/start.sh && \
    echo '' >> /app/start.sh && \
    echo '# ---- Fall back to vfs storage driver if overlay2 failed ----' >> /app/start.sh && \
    echo 'if [ $SUCCESS -eq 0 ]; then' >> /app/start.sh && \
    echo '    echo "[start.sh] overlay2 failed; falling back to vfs storage driver"' >> /app/start.sh && \
    echo '    cat /var/log/dockerd.log >&2 || true' >> /app/start.sh && \
    echo '    pkill -f dockerd || true' >> /app/start.sh && \
    echo '    sleep 2' >> /app/start.sh && \
    echo '    rm -f /var/run/docker.pid' >> /app/start.sh && \
    echo '    rm -f /var/run/docker.sock' >> /app/start.sh && \
    echo '    dockerd --storage-driver=vfs > /var/log/dockerd.log 2>&1 &' >> /app/start.sh && \
    echo '    DOCKERD_PID=$!' >> /app/start.sh && \
    echo '' >> /app/start.sh && \
    echo '    MAX_WAIT=60' >> /app/start.sh && \
    echo '    for i in $(seq 1 $MAX_WAIT); do' >> /app/start.sh && \
    echo '        if docker info > /dev/null 2>&1; then' >> /app/start.sh && \
    echo '            SUCCESS=1' >> /app/start.sh && \
    echo '            echo "[start.sh] Docker daemon ready (vfs) after ${i}s"' >> /app/start.sh && \
    echo '            break' >> /app/start.sh && \
    echo '        fi' >> /app/start.sh && \
    echo '        if ! kill -0 $DOCKERD_PID 2>/dev/null; then' >> /app/start.sh && \
    echo '            echo "[start.sh] dockerd (vfs) exited prematurely"' >> /app/start.sh && \
    echo '            cat /var/log/dockerd.log >&2 || true' >> /app/start.sh && \
    echo '            exit 1' >> /app/start.sh && \
    echo '        fi' >> /app/start.sh && \
    echo '        sleep 1' >> /app/start.sh && \
    echo '    done' >> /app/start.sh && \
    echo 'fi' >> /app/start.sh && \
    echo '' >> /app/start.sh && \
    echo 'if [ $SUCCESS -eq 0 ]; then' >> /app/start.sh && \
    echo '    echo "[start.sh] FATAL: Docker daemon failed to start with both overlay2 and vfs"' >> /app/start.sh && \
    echo '    cat /var/log/dockerd.log >&2 || true' >> /app/start.sh && \
    echo '    exit 1' >> /app/start.sh && \
    echo 'fi' >> /app/start.sh && \
    echo '' >> /app/start.sh && \
    echo '# ---- Launch the Flask application via Gunicorn ----' >> /app/start.sh && \
    echo '# Gunicorn flags rationale:' >> /app/start.sh && \
    echo '#   --bind 0.0.0.0:8080      Cloud Run required listener address' >> /app/start.sh && \
    echo '#   --workers 2              two pre-fork workers per instance' >> /app/start.sh && \
    echo '#   --threads 4              four threads per worker (IO-bound async pipeline)' >> /app/start.sh && \
    echo '#   --timeout 3600           1h timeout matches Cloud Run max request timeout' >> /app/start.sh && \
    echo '#   --graceful-timeout 60    SIGTERM grace window for in-flight requests' >> /app/start.sh && \
    echo '#   --keep-alive 5           keep TCP connections alive (helps health probes)' >> /app/start.sh && \
    echo '#   --access/error-logfile - log to stdout/stderr for Cloud Logging capture' >> /app/start.sh && \
    echo '#   --log-level info         standard verbosity' >> /app/start.sh && \
    echo '#   wsgi:app                 load `app` from wsgi.py at the project root' >> /app/start.sh && \
    echo 'exec gunicorn --bind 0.0.0.0:8080 --workers 2 --threads 4 --timeout 3600 --graceful-timeout 60 --keep-alive 5 --access-logfile - --error-logfile - --log-level info wsgi:app' >> /app/start.sh && \
    chmod +x /app/start.sh

# ---------------------------------------------------------------------------
# Container entrypoint — start.sh wraps Gunicorn with Docker-in-Docker setup
# so the LangGraph pipeline can run sandboxed code via the bash tool.
# ---------------------------------------------------------------------------
CMD ["/app/start.sh"]
