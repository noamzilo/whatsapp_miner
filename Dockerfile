FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
		curl \
		build-essential \
		&& rm -rf /var/lib/apt/lists/*

# Install Poetry 2.1.3 exactly
RUN curl -sSL https://install.python-poetry.org | python3 - --version 2.1.3
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy poetry files first for caching
COPY pyproject.toml poetry.toml ./

# Install deps (no virtualenv, use system)
RUN poetry config virtualenvs.create false && \
	poetry install --no-interaction --no-ansi --only main

# Copy your source code
COPY src ./src

# Copy entrypoint scripts
COPY entrypoint_whatsapp_miner.sh /entrypoint_whatsapp_miner.sh
COPY entrypoint_message_classifier.sh /entrypoint_message_classifier.sh
RUN chmod +x /entrypoint_whatsapp_miner.sh /entrypoint_message_classifier.sh

# Default entrypoint (can be overridden in docker-compose)
ENTRYPOINT ["/entrypoint_whatsapp_miner.sh"]
