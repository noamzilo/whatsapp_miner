# Environment Variable Strategy

## Overview
All environments use `.env` files as the universal interface for secrets and configuration.

## File Structure

### Persistent Files (gitignored)
- **`.env.dev`**: Dev environment secrets (from Doppler `dev_personal`)
- **`.env.prod`**: Prod environment secrets (from Doppler `prd`)

### Template Files (committed)
- **`.env.example`**: Template showing required variables (values removed)

**Note**: There's no separation between "env" and "secrets" files - they contain identical data from the same source (Doppler).

## Deployment Modes

### 1. Local Development (`make dev-local`)
```
Doppler (dev_personal) → .env.dev → docker-compose-with-env.sh → Docker Compose (dev)
```
- Every run updates `.env.dev` from Doppler (docker format, unquoted)
- Helper script loads `.env.dev`, exports vars, passes to compose
- Uses `docker-compose.dev.yml` overlay (volume mounts, ports exposed)
- File persists between runs for inspection

### 2. Local Production Testing (`make prod-local`)
```
Doppler (prd) → .env.prod → docker-compose-with-env.sh → Docker Compose (prod)
```
- Every run updates `.env.prod` from Doppler
- Helper script loads `.env.prod`, exports vars, passes to compose
- Uses `docker-compose.prod.yml` overlay (restart policies, resource limits)
- File persists between runs for inspection

### 3. Act Testing (`make dev-deploy` or `make prod-deploy`)
```
Doppler → .env.dev/.env.prod → Act → GitHub Actions → .env.dev/.env.prod on remote
```
- `sync-secrets` updates `.env.dev` and `.env.prod` from Doppler
- Act reads `.env.dev` or `.env.prod` as GitHub Secrets
- Workflow creates `.env.dev` or `.env.prod` on remote EC2
- Remote runs with the same env file name as local (no difference)

### 4. GitHub Actions (CI/CD)
```
GitHub Secrets (synced from Doppler) → .env.dev/.env.prod on remote → Docker Compose
```
- GitHub Secrets are synced from Doppler via Doppler GitHub integration
- Workflow creates `.env.dev` or `.env.prod` on remote EC2 from GitHub Secrets
- SSH to remote, run compose with environment-specific file
- **Remote uses same file names as local** - no `.env` generic file

## Helper Script: `scripts/docker-compose-with-env.sh`

**Purpose**: Load environment variables from a .env file and run docker compose

**What it does**:
1. Converts `.env` path to absolute
2. Exports `ENV_FILE` variable for compose substitution
3. Quotes values with spaces for safe bash sourcing
4. Exports all vars to environment (for compose variable substitution)
5. Runs `docker compose` with all vars available

**Why it's needed**:
- Docker Compose needs vars in TWO places:
  - **Compose file substitution**: `${VAR_NAME}` in YAML (needs env vars)
  - **Container environment**: Variables inside containers (uses `env_file`)
- Bash `source` fails on unquoted values with spaces
- Different paths when calling from different directories

## Docker Compose Configuration

### Base: `docker/docker-compose.yml`
- Uses `env_file: ${ENV_FILE}` to inject ALL vars into containers
- Uses `${VAR_NAME}` substitution for compose-level vars (image names, container names, etc.)
- Includes migrate, miner, classifier services

### Dev Overlay: `docker/docker-compose.dev.yml`
- Volume mounts for hot reload
- Exposed ports for health checks
- `target: dev` for multi-stage Dockerfile
- No restart policies (easier debugging)

### Prod Overlay: `docker/docker-compose.prod.yml`
- No volume mounts (code baked into image)
- `target: prod` for lean images
- `restart: unless-stopped`
- Resource limits (CPU, memory)
- Log rotation

## Makefile Targets

### Local Development
- `make dev-local`: Start dev locally (foreground)
- `make dev-local-detached`: Start dev locally (background)
- `make prod-local`: Start prod locally (foreground)
- `make prod-local-detached`: Start prod locally (background)

### Remote Deployment Testing
- `make dev-deploy`: Test dev deployment with act (to remote)
- `make prod-deploy`: Test prod deployment with act (to remote)

### Secrets
- `make sync-secrets`: Update `.env.dev` and `.env.prod` from Doppler
- `make generate-env-example`: Generate `.env.example` template

### Utilities
- `make health`: Check service health
- `make logs`: Tail logs
- `make clean`: Remove containers and volumes
- `make ps`: Show container status

**Note**: Every local run automatically updates the env file from Doppler. `sync-secrets` is only needed for act testing.

## Secret Format

### Doppler Format: `docker`
- Unquoted values: `KEY=value`
- Used for `.env.dev`, `.env.prod`, `.secrets.*`
- No quotes to remove, handles spaces correctly

### Why not `env` format?
- `env` format adds quotes: `KEY="value"`
- Quotes cause issues with:
  - Bash sourcing (needs complex sed regex)
  - Docker Compose variable substitution
  - Container name generation

## Remote Deployment Flow

### GitHub Actions → Remote
1. GitHub Actions workflow starts
2. Creates `.env.dev` or `.env.prod` from GitHub Secrets (based on ENV_NAME)
3. SCPs `.env.dev` or `.env.prod` to remote EC2
4. SCPs `docker-compose-with-env.sh` to remote
5. SSH to remote: `./docker-compose-with-env.sh .env.dev -f docker-compose.yml up -d`
6. Remote runs compose with environment-specific file

### Act → Remote (for testing)
1. Act reads `.env.dev` or `.env.prod` as secrets
2. Same as GitHub Actions flow above
3. File names match between local and remote

## Benefits

1. **Universal Interface**: `.env` file works everywhere
2. **No Secret Duplication**: Single source of truth (Doppler), no separate "secrets" files
3. **Easy Testing**: `act` uses same workflow as GitHub Actions
4. **Clean Separation**: Dev/prod configs are separate files (`.env.dev`, `.env.prod`)
5. **Transparent**: Can inspect `.env.dev` or `.env.prod` locally
6. **Standard**: Uses standard Docker Compose `env_file` feature
7. **Flexible**: Can override specific vars in compose overlays
8. **Consistent Naming**: Remote uses same file names as local (`.env.dev`, `.env.prod`)
9. **Auto-Update**: Every local run updates env file from Doppler
10. **Persistent**: Files persist between runs for debugging and inspection

