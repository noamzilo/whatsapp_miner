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

### 4. Doppler Integration
- All secrets managed through either Doppler or github actions secrets
- Wrapper scripts inject Doppler context
- in Github actions, seccrets come through their system
- Consistent variable unquoting across all scripts
- all script use environment variables, and they shouldn't know how the environment is set.

## File Responsibilities

### Core Scripts

#### `docker_build.sh`
- **Purpose**: Build Docker images using docker-compose
- **Key Features**:
  - `--env dev|prd`: Environment-specific builds
  - `--push`: Push to ECR (with automatic authentication)
  - Creates environment-specific image tags
  - Tags with base name for compatibility
- **ECR Auth**: Handles authentication when `--push` is used

#### `docker_run_core.sh`
- **Purpose**: Local container orchestration using docker-compose
- **Key Features**:
  - Starts/restarts services based on image changes
  - Health-checking of all services
  - Cleanup of orphaned containers
  - Digest verification for deployments
- **ECR Auth**: Handles authentication for image pulling

#### `docker_run.sh`
- **Purpose**: Entry point for running containers
- **Key Features**:
  - `--env dev|prd`: Environment selection
  - `--remote`: Deploy to EC2 via SSH
  - Delegates to appropriate wrapper (local vs remote)
- **Modes**:
  - Local: Calls `docker_run_with_doppler.sh`
  - Remote: Copies scripts and executes on EC2

### Wrapper Scripts

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

#### `docker_deploy.sh`
- **Purpose**: Full deployment pipeline
- **Key Features**:
  - Builds and pushes images
  - Runs database migrations
  - Deploys to remote host
  - Shows final status

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
- **Solution**: Doppler integration with proper variable unquoting
- **Implementation**: Wrapper scripts ensure Doppler context and clean variables

### 4. **Container Orchestration**
- **Problem**: Manual container management and inconsistent startup
- **Solution**: docker-compose as the single source of truth
- **Implementation**: All container operations go through docker-compose

### 5. **Deployment Verification**
- **Problem**: No way to verify successful deployments
- **Solution**: Image digest verification and health checks
- **Implementation**: `NEW_IMAGE_DIGEST` tracking and container status monitoring

## Usage Examples

### Local Development
```bash
# Build without push
./docker_build_with_doppler.sh

# Build and push to ECR
./docker_build_with_doppler.sh --push

# Run locally
./docker_run_with_doppler.sh
```

### Production Deployment
```bash
# Full deployment (build, push, migrate, deploy)
./docker_deploy_with_doppler.sh --env prd

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

1. **Consistency**: All scripts use the same authentication and variable handling
2. **Extensibility**: Easy to add new services via docker-compose.yml
3. **Reliability**: Proper error handling and verification at each step
4. **Maintainability**: Clear separation of concerns and well-documented responsibilities
5. **Security**: Proper secret management through Doppler integration 