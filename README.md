# WhatsApp Miner

A Python application for mining and processing WhatsApp data with AI-powered message classification.

## Architecture

The system consists of two main long-running services:

- **Miner**: Continuously monitors and processes WhatsApp messages
- **Classifier**: Performs AI-powered classification of messages using LLM models

Both services run as Docker containers and are designed for continuous operation.

## Environment Management

This project uses **Doppler** for environment variable management and is deployed on **AWS EC2**.

### Doppler Configuration

- **Project**: `whatsapp_miner_backend`
- **Configs**: `dev` (development), `stg` (staging), `prd` (production)

### Required Environment Variables

The following variables must be configured in Doppler:

**Database:**
- `SUPABASE_DATABASE_CONNECTION_STRING_SESSION_POOLER`
- `SUPABASE_DATABASE_PASSWORD`
- `SUPABASE_PSQL_COMMAND`

**AWS EC2:**
- `AWS_EC2_HOST_ADDRESS`
- `AWS_EC2_PEM_CHATBOT_SA_B64`
- `AWS_EC2_REGION`
- `AWS_EC2_USERNAME`
- `AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER`
- `AWS_IAM_WHATSAPP_MINER_ACCESS_KEY`
- `AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID`

**Docker:**
- `DOCKER_COMPOSE_SERVICES`
- `DOCKER_CONTAINER_NAME_WHATSAPP_CLASSIFIER`
- `DOCKER_CONTAINER_NAME_WHATSAPP_MINER`
- `DOCKER_IMAGE_NAME_WHATSAPP_CLASSIFIER`
- `DOCKER_IMAGE_NAME_WHATSAPP_MINER`

**External APIs:**
- `GREEN_API_INSTANCE_API_TOKEN`
- `GREEN_API_INSTANCE_ID`
- `GROQ_API_KEY`

**Configuration:**
- `BUILD_TARGET`
- `ENV_NAME`
- `MESSAGE_CLASSIFIER_RUN_EVERY_SECONDS`

## Development

This project uses Poetry for dependency management. See `pyproject.toml` for dependencies.

### Using the Makefile

The project includes a comprehensive Makefile for managing all aspects of development, deployment, and operations:

```bash
# View all available commands
make help

# Local development
make dev-local

# Check service health
make health-local

# View logs
make logs-dev

# Database operations
make psql-dev
make run-migrations-dev

# Remote operations
make ssh-stage
make ssh-prod

and more.
```

### Development Containers & PyCharm Integration

The development environment exposes SSH ports for direct container access, enabling PyCharm remote development:

**Default SSH Ports:**
- **Dev environment**: 
  - Miner: `localhost:911`
  - Classifier: `localhost:912`
- **Staging environment**: 
  - Miner: `localhost:921`
  - Classifier: `localhost:922`
- **Production environment**: 
  - Miner: `localhost:931`
  - Classifier: `localhost:932`

**Custom Port Configuration:**
```bash
# Use custom ports
make dev-local PORTS=876,765

# Or specify individual ports
make dev-local MINER_PORT=876 CLASSIFIER_PORT=765
```

**PyCharm SSH Interpreter Setup:**
1. Sync environment secrets: `make sync-secrets-env`
2. Start the dev environment: `make dev-local`
3. In PyCharm, go to Settings → Project → Python Interpreter
4. Add New Interpreter → SSH Interpreter
5. Configure connection:
   - Host: `localhost`
   - Port: `911` (miner) or `912` (classifier)
   - Username: `root`
   - Password: `root`
6. Set interpreter path: `/app/.venv/bin/python`
7. Configure path mappings:
   - Local project root (`whatsapp_miner/`) → Remote path (`/app`)
   - This ensures PyCharm can properly index the virtual environment
8. Point PyCharm to use the synced environment variables from `docker/.env.dev`

**Container Access:**
```bash
# Shell into containers directly
make docker-exec-miner-dev-local
make docker-exec-classifier-dev-local
```

### Key Makefile Features

- **Multi-environment support**: dev, staging, prod
- **Local and remote deployment**: Docker Compose with environment-specific configurations
- **Health monitoring**: Container status and service health checks
- **Database management**: Migrations, connections, and maintenance
- **Log management**: View and tail logs for all services
- **Secret synchronization**: Automatic Doppler secret updates
- **Container management**: Start, stop, restart, and clean operations

## Deployment

The system is designed to run on AWS EC2 with Docker Compose. All deployment operations are managed through the Makefile, which handles:

- Environment-specific configurations
- Secret management via Doppler
- Container orchestration
- Database migrations
- Health monitoring


