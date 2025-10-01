# CI/CD Deployment Guide

## Overview

The CI/CD pipeline is simplified and standard, using Docker Compose and environment-specific `.env` files everywhere.

## Workflow Structure

### Triggers

1. **Manual Deployment** (workflow_dispatch):
   - Can choose `dev` or `prod` environment
   - Useful for hotfixes or manual releases

2. **Automatic Deployment** (push):
   - Push to `dev` branch → deploys to dev
   - Push to `main` branch → deploys to prod

### Pipeline Steps

```
┌─────────────────────────────────────────────────┐
│ 1. Setup                                        │
│    - Checkout code                              │
│    - Configure AWS credentials                  │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ 2. Build & Push Images                          │
│    - Login to ECR                               │
│    - Build miner image (prod target)            │
│    - Build classifier image (prod target)       │
│    - Push with tags: env-sha & env             │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ 3. Deploy to EC2                                │
│    - Create .env.dev or .env.prod from secrets  │
│    - Setup SSH key                              │
│    - Copy files to remote:                      │
│      • docker-compose.yml                       │
│      • docker-compose.prod.yml                  │
│      • docker-compose-with-env.sh               │
│      • .env.dev or .env.prod                    │
│    - SSH to remote and deploy                   │
│    - Verify deployment (health checks)          │
└─────────────────────────────────────────────────┘
```

## Environment Files

### Local
- `.env.dev` - Dev environment (from Doppler)
- `.env.prod` - Prod environment (from Doppler)

### Remote (EC2)
- `.env.dev` - Dev environment (from GitHub Secrets)
- `.env.prod` - Prod environment (from GitHub Secrets)

**Same file names everywhere!** No difference between local and remote.

## GitHub Secrets Required

All secrets are synced from Doppler to GitHub via Doppler's GitHub integration.

### AWS/Infrastructure
- `AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID`
- `AWS_IAM_WHATSAPP_MINER_ACCESS_KEY`
- `AWS_EC2_REGION`
- `AWS_EC2_HOST_ADDRESS`
- `AWS_EC2_USERNAME`
- `AWS_EC2_PEM_CHATBOT_SA_B64` (base64 encoded SSH key)
- `AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER`

### Docker
- `DOCKER_IMAGE_NAME_WHATSAPP_MINER`
- `DOCKER_IMAGE_NAME_WHATSAPP_CLASSIFIER`
- `DOCKER_CONTAINER_NAME_WHATSAPP_MINER`

### Application
- `GREEN_API_INSTANCE_API_TOKEN`
- `GREEN_API_INSTANCE_ID`
- `SUPABASE_DATABASE_CONNECTION_STRING`
- `SUPABASE_DATABASE_CONNECTION_STRING_SESSION_POOLER`
- `SUPABASE_DATABASE_PASSWORD`
- `SUPABASE_PSQL_COMMAND`
- `MESSAGE_CLASSIFIER_RUN_EVERY_SECONDS`
- `GROQ_API_KEY`

## Testing Locally with Act

### Install Act
```bash
# macOS
brew install act

# Linux
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
```

### Test Dev Deployment
```bash
make sync-secrets  # Update .env.dev from Doppler
make dev-deploy    # Test deployment with act
```

### Test Prod Deployment
```bash
make sync-secrets   # Update .env.prod from Doppler
make prod-deploy    # Test deployment with act
```

## Deployment Commands

### From Local Machine
```bash
# Test locally first
make dev-local-detached
make health

# Test deployment to remote (with act)
make dev-deploy
```

### From GitHub Actions
Push to branch:
```bash
# Deploy dev
git push origin dev

# Deploy prod
git push origin main
```

Manual trigger:
1. Go to Actions tab in GitHub
2. Select "Deploy WhatsApp Miner" workflow
3. Click "Run workflow"
4. Choose environment (dev/prod)
5. Click "Run workflow"

## Remote Deployment Process

When the workflow runs on EC2:

```bash
# 1. Files are copied to remote
/home/ubuntu/whatsapp_miner/
├── docker-compose.yml
├── docker-compose.prod.yml
├── docker-compose-with-env.sh
└── .env.dev or .env.prod

# 2. Login to ECR
aws ecr get-login-password --region us-east-1 | docker login ...

# 3. Pull latest images
./docker-compose-with-env.sh .env.dev -f docker-compose.yml -f docker-compose.prod.yml pull

# 4. Deploy
./docker-compose-with-env.sh .env.dev -f docker-compose.yml -f docker-compose.prod.yml up -d --no-build

# 5. Verify
docker ps --filter "name=whatsapp_miner"
```

## Health Checks

The workflow has robust health check verification:

### Process
1. Initial wait: 30 seconds for services to start
2. Health check loop: Up to 2 minutes, checking every 10 seconds
3. Both services must report `healthy` status

### Success Criteria
- Miner container: Status shows `(healthy)`
- Classifier container: Status shows `(healthy)`

### Failure Handling
If health checks fail, the pipeline:
1. **Exits with error code 1** (fails the deployment)
2. **Shows detailed diagnostics**:
   - Container status for all services
   - Last 100 lines of miner logs
   - Last 100 lines of classifier logs
   - Migration logs
3. **Previous containers keep running** (no automatic rollback)

### Example Failure Output
```
❌ ERROR: Health check timeout after 120s

Container status:
CONTAINER ID   IMAGE     STATUS
abc123         miner     Up 2 minutes (unhealthy)
def456         class     Up 2 minutes (healthy)

Miner logs (last 100 lines):
[error details here...]
```

This ensures you can immediately see what went wrong without SSHing to the server.

## Rollback

If deployment fails, the previous containers continue running (unless they were stopped).

To manually rollback:
```bash
# SSH to EC2
ssh -i your-key.pem ubuntu@your-ec2-host

cd /home/ubuntu/whatsapp_miner

# Check previous images
docker images | grep whatsapp_miner

# Pull specific version
docker pull your-registry/whatsapp_miner:dev-abc123

# Update .env.dev to use specific tag
# Then redeploy
./docker-compose-with-env.sh .env.dev -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Deployment fails at build stage
- Check Docker build logs in GitHub Actions
- Verify Dockerfile syntax
- Check Poetry dependencies in `pyproject.toml`

### Deployment fails at push stage
- Verify AWS credentials are correct
- Check ECR repository exists
- Verify IAM permissions for ECR push

### Deployment fails at remote stage
- Check SSH key is correct (base64 encoded)
- Verify EC2 instance is running
- Check security group allows SSH (port 22)
- Verify working directory exists and has permissions

### Containers fail to start on remote
- SSH to EC2 and check logs:
  ```bash
  docker logs whatsapp_miner_miner_prod
  docker logs whatsapp_miner_classifier_prod
  ```
- Check environment variables in `.env.dev` or `.env.prod`
- Verify database connection strings
- Check ECR image pull permissions

### Health checks fail
- Verify health endpoints are working:
  ```bash
  curl http://localhost:8000/health  # Miner
  curl http://localhost:8001/health  # Classifier
  ```
- Check container logs for errors
- Verify database migrations completed

## Benefits of New Approach

1. **Simple**: Standard Docker Compose workflow
2. **Consistent**: Same file names and process local/remote
3. **Testable**: Use `act` to test deployments locally
4. **Maintainable**: No custom bash scripts to maintain
5. **Transparent**: All steps visible in GitHub Actions UI
6. **Reliable**: Health checks ensure deployment success
7. **Auditable**: All deployments tracked in GitHub

