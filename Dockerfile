FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
		build-essential \
		curl \
		&& rm -rf /var/lib/apt/lists/*

# Install Poetry
ENV POETRY_VERSION=1.8.2
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy poetry files first for caching
COPY pyproject.toml poetry.lock poetry.toml ./

# Install deps (no virtualenv, use system)
RUN poetry config virtualenvs.create false && \
	poetry install --no-interaction --no-ansi --only main

# Now copy your source code
COPY src ./src

# Copy entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Entrypoint
ENTRYPOINT ["/entrypoint.sh"]
