# ════════════════════════════════════════════════════════════════════════════
# Multi-stage Dockerfile for WhatsApp Miner
# Stages: base (shared dependencies) → dev (with dev tools) → prod (lean)
# ════════════════════════════════════════════════════════════════════════════

# ────────────────────────────────────────────────────────────────────────────
# Base Stage: Common dependencies for both dev and prod
# ────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim as base

# Install system dependencies (build tools needed for some Python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    postgresql-client \
    awscli \
    && rm -rf /var/lib/apt/lists/*

# Install uv (pinned; copied from the official distroless image)
COPY --from=ghcr.io/astral-sh/uv:0.12.3 /uv /usr/local/bin/uv

# Put the project venv first on PATH so `python`/`alembic` resolve to it
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app
# Copy instead of hardlink: the build context and cache sit on different mounts
ENV UV_LINK_MODE=copy

WORKDIR /app

# Copy dependency manifests for resolution
COPY pyproject.toml uv.lock README.md ./

# ────────────────────────────────────────────────────────────────────────────
# Dev Stage: Includes dev dependencies and tools
# ────────────────────────────────────────────────────────────────────────────
FROM base as dev

# Install ALL dependencies including dev tools
RUN uv sync --frozen

# Install SSH server and required tools for PyCharm remote development
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Configure SSH server for PyCharm remote development
RUN mkdir -p /var/run/sshd && \
    echo 'root:root' | chpasswd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config && \
    echo 'Port 2222' >> /etc/ssh/sshd_config && \
    echo 'X11Forwarding yes' >> /etc/ssh/sshd_config && \
    echo 'X11DisplayOffset 10' >> /etc/ssh/sshd_config

# make ssh connection faster
RUN echo 'UseDNS no' >> /etc/ssh/sshd_config && \
    echo 'GSSAPIAuthentication no' >> /etc/ssh/sshd_config

# Create SSH directory and set permissions
RUN mkdir -p /root/.ssh && \
    chmod 700 /root/.ssh

# Add ll alias to bashrc
RUN echo 'alias ll="ls -la"' >> /root/.bashrc

# Copy source code (will be overridden by volume mount in dev)
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./

# Copy entrypoint scripts
COPY entrypoint_whatsapp_miner.sh /entrypoint_whatsapp_miner.sh
COPY entrypoint_message_classifier.sh /entrypoint_message_classifier.sh
COPY entrypoint_db_backup.sh /entrypoint_db_backup.sh
COPY docker/run_migration_and_exit.sh /db/run_migration_and_exit.sh
RUN chmod +x /entrypoint_whatsapp_miner.sh /entrypoint_message_classifier.sh /entrypoint_db_backup.sh /db/run_migration_and_exit.sh

# Default entrypoint (can be overridden in docker-compose)
ENTRYPOINT ["/entrypoint_whatsapp_miner.sh"]

# ────────────────────────────────────────────────────────────────────────────
# Production Stage: Lean image with only runtime dependencies
# ────────────────────────────────────────────────────────────────────────────
FROM base as prod

# Install ONLY production dependencies (no dev tools)
RUN uv sync --frozen --no-dev

# Remove build tools to reduce image size
RUN apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy source code (baked into image, no volume mounts in production)
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./

# Copy entrypoint scripts
COPY entrypoint_whatsapp_miner.sh /entrypoint_whatsapp_miner.sh
COPY entrypoint_message_classifier.sh /entrypoint_message_classifier.sh
COPY entrypoint_db_backup.sh /entrypoint_db_backup.sh
COPY docker/run_migration_and_exit.sh /db/run_migration_and_exit.sh
RUN chmod +x /entrypoint_whatsapp_miner.sh /entrypoint_message_classifier.sh /entrypoint_db_backup.sh /db/run_migration_and_exit.sh

# Default entrypoint (can be overridden in docker-compose)
ENTRYPOINT ["/entrypoint_whatsapp_miner.sh"]

