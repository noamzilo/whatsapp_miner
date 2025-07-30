# Deployment Architecture Design

## Overview
This document describes the improved deployment architecture that supports three deployment modes:
1. **Local Development** - Uses Doppler for secrets
2. **Remote Deployment** - Uses Doppler secrets sent via SSH
3. **GitHub Actions** - Uses GitHub secrets to create .env file

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
    ↓ (builds, pushes, and deploys)
docker_run.sh --remote
    ↓ (SSH to remote)
docker_remote_run.sh
    ↓ (loads .env and runs core)
docker_run_core.sh
    ↓ (runs docker-compose)
docker-compose.yml
```

### GitHub Actions Flow (Future)
```
GitHub Actions
    ↓ (creates .env from secrets)
docker_deploy.sh
    ↓ (builds, pushes, and deploys)
docker_run.sh --remote
    ↓ (SSH to remote)
docker_remote_run.sh
    ↓ (loads .env and runs core)
docker_run_core.sh
    ↓ (runs docker-compose)
docker-compose.yml
```

## Key Improvements

### 1. Deployment Verification
- `docker_deploy.sh` captures the new image digest
- `docker_remote_run.sh` verifies the new image is running
- Deployment fails if verification fails

### 2. Clean Separation of Concerns
- **Local**: `docker_run_with_doppler.sh` handles Doppler integration
- **Remote**: `docker_remote_run.sh` handles .env file loading
- **Core**: `docker_run_core.sh` handles docker-compose execution

### 3. Environment Agnostic
- Local uses Doppler secrets directly
- Remote uses .env file (from Doppler or GitHub Actions)
- Core script works with any .env file source

## Script Responsibilities

### Entry Points
- `docker_deploy_with_doppler.sh` - Local deployment entry point
- `docker_run.sh` - Local/remote execution router

### Local Development
- `docker_run_with_doppler.sh` - Doppler integration for local runs
- `docker_build_with_doppler.sh` - Doppler integration for builds

### Remote Execution
- `docker_remote_run.sh` - Remote environment setup and core execution
- `docker_run_core.sh` - Docker Compose execution (shared by local/remote)

### Deployment
- `docker_deploy.sh` - Build, push, and deploy with verification
- `docker_build.sh` - Simple Docker build

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

## Benefits of This Design

1. **Clear Separation**: Local vs remote concerns are separated
2. **Environment Agnostic**: Core script works with any .env source
3. **Verification**: Deployment success is verified automatically
4. **Maintainable**: Each script has a single responsibility
5. **Extensible**: Easy to add GitHub Actions or other CI/CD systems 