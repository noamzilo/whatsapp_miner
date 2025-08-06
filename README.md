# WhatsApp Miner

A Python application for mining and processing WhatsApp data.

## Installation

This project uses Poetry for dependency management. See `pyproject.toml` for dependencies.

## Development

The project includes Docker support for containerized deployment.

## Deployment

### Local Deployment

For local development and testing:

```bash
# Deploy to local environment (dev)
./deploy.sh --env dev

# Deploy to production environment
./deploy.sh --env prd
```

### Remote Deployment

For remote deployment to EC2:

```bash
# Deploy to remote dev environment
./docker_run.sh --env dev --remote

# Deploy to remote production environment  
./docker_run.sh --env prd --remote
```

### Manual Steps

If you need to run individual steps:

```bash
# Build and push Docker image
./docker_build.sh --env dev --push

# Run database migrations
./run_migrations.sh --env ${ENV_NAME}

# Start services locally
./docker_run.sh --env dev

# Validate deployment setup
./docker_validate_setup.sh --env dev
```

## Environment Configuration

This project uses Doppler for environment variable management:

- **Project**: `whatsapp_miner_backend`
- **Config**: `dev_personal` (local), `prd` (production)

Make sure Doppler is configured and you have access to the project secrets.

### Variable Management

The project includes automatic unquoting of Doppler variables to handle cases where variables may have surrounding quotes. This is handled by the `docker_utils.sh` utility script and applied in all `*_with_doppler.sh` scripts.


