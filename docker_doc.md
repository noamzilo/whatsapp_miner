# Docker Deployment Documentation

## Overview

This document explains the Docker deployment system for the WhatsApp Miner project. The system is designed around **docker-compose** as the central orchestration tool, with clear separation of concerns between local and remote operations.

## Main Design Principles

### 1. Docker-Compose Centric
- **No plain `docker run` commands** in any script
- All container management goes through `docker-compose.yml`
- Easy to extend with additional services
- Consistent environment variable injection

### 2. Environment Separation
- **dev** and **prd** environments with distinct image tags
- Environment-specific image names: `image:dev` and `image:prd`
- Separate configuration and secrets per environment
- ALL scripts and code must be environment agnostic.

### 3. ECR Authentication Consistency
- All scripts use **AWS CLI approach** for ECR authentication
- Consistent variable mapping: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`
- No more `AWS_ECR_LOGIN_PASSWORD` or `AWS_ECR_REGISTRY` variables

**Doppler Variable Aliasing:**
Due to Doppler's custom variable naming, the following aliases are required in all scripts:

| Doppler Variable | Standard AWS Variable | Purpose |
|------------------|----------------------|---------|
| `AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID` | `AWS_ACCESS_KEY_ID` | AWS Access Key for ECR authentication |
| `AWS_IAM_WHATSAPP_MINER_ACCESS_KEY` | `AWS_SECRET_ACCESS_KEY` | AWS Secret Key for ECR authentication |
| `AWS_EC2_REGION` | `AWS_DEFAULT_REGION` | AWS Region for ECR operations |

**Implementation in Scripts:**
```bash
# Map Doppler variables to standard AWS names
export AWS_ACCESS_KEY_ID="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$AWS_IAM_WHATSAPP_MINER_ACCESS_KEY"
export AWS_DEFAULT_REGION="$AWS_EC2_REGION"
```

This mapping ensures compatibility with AWS CLI commands like `aws ecr get-login-password` and `docker login`.

### 4. Environment Agnostic Core Scripts
**CRITICAL**: The core scripts (`docker_build.sh`, `docker_deploy.sh`, `docker_run.sh`) are **completely environment agnostic**. They:
- **Cannot be run directly** - they must be invoked through wrapper scripts
- **Get all environment variables from wrapper scripts** - they don't know about Doppler vs GitHub Actions
- **Expect environment variables to be already set** - no environment detection logic
- **Work identically in all contexts** - local development, GitHub Actions, remote deployment

### 5. Wrapper Script Pattern
The system uses a **wrapper pattern** where:
- **Wrapper scripts** provide environment context (Doppler for local, GitHub Actions for CI/CD)
- **Core scripts** are environment agnostic and receive variables through environment
- **Entry points** are always the wrapper scripts, never the core scripts directly

**Wrapper Scripts:**
- `docker_build_with_doppler.sh` → `docker_build.sh`
- `docker_deploy_with_doppler.sh` → `docker_deploy.sh`
- `docker_run_with_doppler.sh` → `docker_run.sh`
- `.github/workflows/deploy.yml` → `docker_deploy.sh` (via secrets blob)

### 6. GitHub Actions Integration
- **Environment agnostic workflow** - `deploy.yml` packs secrets into base64 blob
- **Simplified dependency installation** - Installs Alembic and psycopg2-binary directly via pip (no Poetry required)
- **Secret verification** - Validates all required secrets before deployment
- **Uses the scripts** - Delegates all logic to the deployment scripts

### 7. Local Testing with Act
- **`deploy_with_act.sh`** - Wrapper to fake GitHub Actions environment locally
- **Environment simulation** - Makes Act think it's running in GitHub Actions
- **Secret injection** - Uses Doppler secrets to simulate GitHub Actions secrets
- **Local debugging** - Allows testing GitHub Actions workflow locally

## File Responsibilities

### Core Scripts (Environment Agnostic)

#### `docker_build.sh`
- **Purpose**: Build Docker images using docker-compose
- **Key Features**:
  - `--env dev|prd`: Environment-specific builds
  - `--push`: Push to ECR (with automatic authentication)
  - Creates environment-specific image tags
  - Tags with base name for compatibility
- **ECR Auth**: Handles authentication when `--push` is used
- **Environment**: Completely agnostic - gets all variables from wrapper

#### `docker_run_core.sh`
- **Purpose**: Local container orchestration using docker-compose
- **Key Features**:
  - Starts/restarts services based on image changes
  - Health-checking of all services
  - Cleanup of orphaned containers
  - Digest verification for deployments
- **ECR Auth**: Handles authentication for image pulling
- **Environment**: Completely agnostic - gets all variables from wrapper

#### `docker_run.sh`
- **Purpose**: Entry point for running containers
- **Key Features**:
  - `--env dev|prd`: Environment selection
  - `--remote`: Deploy to EC2 via SSH
  - Delegates to appropriate wrapper (local vs remote)
- **Modes**:
  - Local: Calls `docker_run_with_doppler.sh`
  - Remote: Copies scripts and executes on EC2
- **Environment**: Completely agnostic - gets all variables from wrapper

#### `docker_deploy.sh`
- **Purpose**: Full deployment pipeline
- **Key Features**:
  - Builds and pushes images
  - Runs database migrations
  - Deploys to remote host
  - Shows final status
- **Environment**: Completely agnostic - gets all variables from wrapper

### Wrapper Scripts (Environment Aware)

#### `docker_build_with_doppler.sh`
- **Purpose**: Doppler wrapper for building
- **Key Features**:
  - Ensures Doppler context
  - Unquotes environment variables
  - Delegates to `docker_build.sh`

#### `docker_run_with_doppler.sh`
- **Purpose**: Doppler wrapper for local running
- **Key Features**:
  - Validates AWS credentials
  - Generates temporary `.env` file
  - Delegates to `docker_run_core.sh`

#### `docker_deploy_with_doppler.sh`
- **Purpose**: Doppler wrapper for full deployment
- **Key Features**:
  - Full deployment pipeline
  - Delegates to `docker_deploy.sh`

### Remote Deployment

#### `docker_remote_run.sh`
- **Purpose**: Executes on EC2 remote host
- **Key Features**:
  - Loads environment from passed `.env` file
  - Maps AWS credentials
  - Delegates to `docker_run_core.sh`
  - Verifies deployment with image digests

### Docker Compose

#### `docker-compose.yml`
- **Purpose**: Central orchestration configuration
- **Services**:
  - `miner`: Main WhatsApp processing service
  - `classifier`: Message classification service
- **Features**:
  - Environment-specific container naming
  - Environment variable injection
  - Restart policies
  - Custom entrypoints

### GitHub Actions & Local Testing

#### `.github/workflows/deploy.yml`
- **Purpose**: GitHub Actions workflow for automated deployment
- **Key Features**:
  - **Environment agnostic** - packs secrets into base64 blob
  - Validates all required secrets before deployment
  - Installs minimal dependencies (Alembic and psycopg2-binary via pip)
  - Delegates all logic to deployment scripts
- **Triggers**: Manual dispatch and pushes to main/dev branches

#### `docker_deploy_with_doppler.sh`
- **Purpose**: Local wrapper for full deployment
- **Key Features**:
  - Ensures Doppler context
  - Collects all secrets as JSON → base64
  - Delegates to `docker_deploy.sh`

## Main Concerns Addressed

### 1. **ECR Authentication Issues**
- **Problem**: 403 Forbidden errors when pushing to ECR
- **Solution**: Consistent AWS CLI authentication across all scripts
- **Implementation**: `aws ecr get-login-password` with proper credential mapping

### 2. **Environment Separation**
- **Problem**: Mixing dev and production configurations
- **Solution**: Environment-specific image tags and container names
- **Implementation**: `image:dev` vs `image:prd` with `ENV_NAME` injection

### 3. **Secret Management**
- **Problem**: Hardcoded secrets and inconsistent variable handling
- **Solution**: Wrapper scripts provide environment context
- **Implementation**: Doppler for local, GitHub Actions secrets for CI/CD

### 4. **Container Orchestration**
- **Problem**: Manual container management and inconsistent startup
- **Solution**: docker-compose as the single source of truth
- **Implementation**: All container operations go through docker-compose

### 5. **Deployment Verification**
- **Problem**: No way to verify successful deployments
- **Solution**: Image digest verification and health checks
- **Implementation**: `NEW_IMAGE_DIGEST` tracking and container status monitoring

### 6. **Environment Agnostic Design**
- **Problem**: Scripts need to work in both local (Doppler) and CI/CD (GitHub Actions) environments
- **Solution**: Core scripts are completely environment agnostic, wrapper scripts provide context
- **Implementation**: Wrapper pattern ensures core scripts work identically in all contexts

### 7. **GitHub Actions Integration**
- **Problem**: Poetry installation permission issues and unnecessary complexity in CI/CD
- **Solution**: Simplified dependency installation and environment agnostic workflow
- **Implementation**: Minimal pip dependencies, secrets packed as base64 blob

### 8. **Local Testing**
- **Problem**: No way to test GitHub Actions workflow locally
- **Solution**: Act wrapper with environment simulation
- **Implementation**: `deploy_with_act.sh` fakes GitHub Actions environment using Doppler secrets

## Usage Examples

### Local Development (Wrapper Scripts Only)
```bash
# Build without push
./docker_build_with_doppler.sh

# Build and push to ECR
./docker_build_with_doppler.sh --push

# Run locally
./docker_run_with_doppler.sh

# Full deployment
./docker_deploy_with_doppler.sh --env dev
```

### Production Deployment
```bash
# Remote deployment only
./docker_run.sh --env prd --remote
```

### Environment-Specific Operations
```bash
# Development environment
./docker_build_with_doppler.sh --env dev --push

# Production environment
./docker_build_with_doppler.sh --env prd --push
```

## Key Benefits

1. **Environment Agnostic**: Core scripts work identically in all contexts
2. **Consistency**: All scripts use the same authentication and variable handling
3. **Extensibility**: Easy to add new services via docker-compose.yml
4. **Reliability**: Proper error handling and verification at each step
5. **Maintainability**: Clear separation of concerns and well-documented responsibilities
6. **Security**: Proper secret management through wrapper scripts
7. **Testability**: Local testing of GitHub Actions workflows via Act 