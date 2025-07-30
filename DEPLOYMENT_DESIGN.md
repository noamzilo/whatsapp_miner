# Deployment Architecture Design

## Overview
This document describes the deployment architecture that supports four deployment modes:
1. **Local Development** - Uses Doppler for secrets
2. **Remote Deployment** - Uses Doppler secrets sent via SSH
3. **Act Deployment** - Uses Act (GitHub Actions locally) with Doppler
4. **GitHub Actions** - Uses GitHub secrets (synced from Doppler)

## Architecture Flow

### Local Development Flow
```
docker_deploy_with_doppler.sh
    ↓ (injects Doppler secrets)
docker_deploy.sh
    ↓ (builds and pushes image)
docker_run.sh (local)
    ↓ (delegates to local runner)
docker_run_with_doppler.sh
    ↓ (creates temp .env from Doppler)
docker_run_core.sh
    ↓ (runs docker-compose)
docker-compose.yml
```

### Remote Deployment Flow
```
docker_deploy_with_doppler.sh
    ↓ (injects Doppler secrets)
docker_deploy.sh
    ↓ (validates setup)
docker_validate_setup.sh
    ↓ (builds and pushes image)
docker_build.sh + docker push
    ↓ (SCP scripts to remote)
docker_run.sh --remote
    ↓ (SSH to remote with SCP)
docker_remote_run.sh
    ↓ (loads .env and runs core)
docker_run_core.sh
    ↓ (runs docker-compose)
docker-compose.yml
    ↓ (verifies deployment)
docker_show_status.sh
```

### Act Deployment Flow (Local GitHub Actions)
```
deploy_with_act.sh
    ↓ (validates setup and downloads runner image)
docker_validate_setup.sh
    ↓ (injects Doppler secrets)
.github/workflows/deploy.yml
    ↓ (GitHub Actions runner)
docker_deploy.sh
    ↓ (validates setup)
docker_validate_setup.sh
    ↓ (builds and pushes image)
docker_build.sh + docker push
    ↓ (SCP scripts to remote)
docker_run.sh --remote
    ↓ (SSH to remote with SCP)
docker_remote_run.sh
    ↓ (loads .env and runs core)
docker_run_core.sh
    ↓ (runs docker-compose)
docker-compose.yml
    ↓ (verifies deployment)
docker_show_status.sh
```

### GitHub Actions Flow (Remote CI/CD)
```
GitHub Actions (.github/workflows/deploy.yml)
    ↓ (GitHub secrets from Doppler sync)
docker_deploy.sh
    ↓ (validates setup)
docker_validate_setup.sh
    ↓ (builds and pushes image)
docker_build.sh + docker push
    ↓ (SCP scripts to remote)
docker_run.sh --remote
    ↓ (SSH to remote with SCP)
docker_remote_run.sh
    ↓ (loads .env and runs core)
docker_run_core.sh
    ↓ (runs docker-compose)
docker-compose.yml
    ↓ (verifies deployment)
docker_show_status.sh
```

## Key Features

### 1. Deployment Verification
- `docker_deploy.sh` captures the new image digest
- `docker_remote_run.sh` verifies the new image is running
- `docker_show_status.sh` shows final deployment status
- Deployment fails if verification fails

### 2. Clean Separation of Concerns
- **Local**: `docker_run_with_doppler.sh` handles Doppler integration
- **Remote**: `docker_remote_run.sh` handles .env file loading
- **Core**: `docker_run_core.sh` handles docker-compose execution

### 3. Environment Agnostic
- Local uses Doppler secrets directly
- Remote uses .env file (from Doppler or GitHub Actions)
- Core script works with any .env file source

### 4. SCP Script Transfer
- `docker_run.sh --remote` uses SCP to transfer scripts to remote
- Transfers: `docker_run_core.sh`, `docker-compose.yml`, `docker_remote_run.sh`
- Creates temporary .env file on remote from Doppler secrets

### 5. Automatic Setup
- Act deployment automatically downloads runner image on first run
- No manual setup steps required
- Test mode available with timeout protection

## Script Responsibilities

### Entry Points
- `docker_deploy_with_doppler.sh` - Local deployment entry point
- `docker_run.sh` - Local/remote execution router
- `deploy_with_act.sh` - Act deployment wrapper (with auto-setup)
- `.github/workflows/deploy.yml` - GitHub Actions workflow

### Local Development
- `docker_run_with_doppler.sh` - Doppler integration for local runs
- `docker_build_with_doppler.sh` - Doppler integration for builds

### Remote Execution
- `docker_remote_run.sh` - Remote environment setup and core execution
- `docker_run_core.sh` - Docker Compose execution (shared by local/remote)

### Deployment
- `docker_deploy.sh` - Build, push, and deploy with verification
- `docker_build.sh` - Simple Docker build

### Utility Scripts
- `docker_validate_setup.sh` - Validates deployment prerequisites
- `docker_show_status.sh` - Shows running containers locally and remotely
- `docker_validate_and_show_status.sh` - Comprehensive validation and status report

## Environment Variables

### Required for All Modes
- `DOCKER_IMAGE_NAME_WHATSAPP_MINER`
- `AWS_EC2_REGION`
- `AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID`
- `AWS_IAM_WHATSAPP_MINER_ACCESS_KEY`

### Remote-Specific
- `AWS_EC2_HOST_ADDRESS`
- `AWS_EC2_USERNAME`
- `AWS_EC2_PEM_CHATBOT_SA_B64`
- `AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER`

### Deployment Verification
- `NEW_IMAGE_DIGEST` - Set by `docker_deploy.sh` for verification

## Usage

### Local Development
```bash
# Deploy and run locally
./docker_deploy_with_doppler.sh

# Run only (no deployment)
./docker_run.sh

# Check container status
doppler run -- ./docker_show_status.sh
```

### Remote Deployment
```bash
# Deploy to remote
./docker_deploy_with_doppler.sh

# Run only on remote
doppler run -- ./docker_run.sh --remote

# Check remote status
doppler run -- ./docker_show_status.sh
```

### Act Deployment (Local GitHub Actions)
```bash
# Normal deployment (auto-setup on first run)
.github/deploy_with_act.sh

# Test deployment with timeout protection
.github/deploy_with_act.sh --test
```

### GitHub Actions Deployment (Remote CI/CD)
```bash
# Triggered by push to main/dev/stage branches
# Uses GitHub secrets synced from Doppler
```

### Validation
```bash
# Validate deployment setup
./docker_validate_setup.sh

# Comprehensive validation and status
./docker_validate_and_show_status.sh
```

## Benefits

1. **Clear Separation**: Local vs remote concerns are separated
2. **Environment Agnostic**: Core script works with any .env source
3. **Verification**: Deployment success is verified automatically
4. **Maintainable**: Each script has a single responsibility
5. **Extensible**: Easy to add GitHub Actions or other CI/CD systems
6. **Multi-Environment**: Supports local, remote, Act, and GitHub Actions
7. **Zero Setup**: Act deployment automatically handles setup on first run 