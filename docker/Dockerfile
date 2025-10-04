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
    && rm -rf /var/lib/apt/lists/*

# Install Poetry 2.1.3 exactly
RUN curl -sSL https://install.python-poetry.org | python3 - --version 2.1.3
ENV PATH="/root/.local/bin:$PATH"
ENV PYTHONPATH=/app

WORKDIR /app

# Copy poetry configuration files for dependency resolution
COPY pyproject.toml poetry.toml poetry.lock README.md ./

# Configure Poetry to not create virtual environments (use system Python)
RUN poetry config virtualenvs.create false

# ────────────────────────────────────────────────────────────────────────────
# Dev Stage: Includes dev dependencies and tools
# ────────────────────────────────────────────────────────────────────────────
FROM base as dev

# Install ALL dependencies including dev tools
RUN poetry install --no-interaction --no-ansi --with dev

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

# Copy source code (will be overridden by volume mount in dev)
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./

# Copy entrypoint scripts
COPY entrypoint_whatsapp_miner.sh /entrypoint_whatsapp_miner.sh
COPY entrypoint_message_classifier.sh /entrypoint_message_classifier.sh
RUN chmod +x /entrypoint_whatsapp_miner.sh /entrypoint_message_classifier.sh

# Default entrypoint (can be overridden in docker-compose)
ENTRYPOINT ["/entrypoint_whatsapp_miner.sh"]

# ────────────────────────────────────────────────────────────────────────────
# Production Stage: Lean image with only runtime dependencies
# ────────────────────────────────────────────────────────────────────────────
FROM base as prod

# Install ONLY production dependencies (no dev tools)
RUN poetry install --no-interaction --no-ansi --only main

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
RUN chmod +x /entrypoint_whatsapp_miner.sh /entrypoint_message_classifier.sh

# Default entrypoint (can be overridden in docker-compose)
ENTRYPOINT ["/entrypoint_whatsapp_miner.sh"]

