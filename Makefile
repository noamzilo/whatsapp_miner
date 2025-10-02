.PHONY: dev-local dev-local-detached prod-local prod-local-detached dev-deploy prod-deploy sync-secrets clean logs shell-miner shell-classifier psql-dev psql-prod run-migrations-dev run-migrations-prod help

# ════════════════════════════════════════════════════════════════════════════
# WhatsApp Miner - Makefile
# ════════════════════════════════════════════════════════════════════════════

# ────────────────────────────────────────────────────────────────────────────
# Local Development (daily use)
# ────────────────────────────────────────────────────────────────────────────

dev-local:
	@echo "🚀 Starting dev environment locally..."
	@echo "📝 Updating .env.dev from Doppler..."
	@doppler secrets download --project whatsapp_miner_backend --config dev --format docker --no-file --silent > .env.dev
	@./scripts/docker-compose-with-env.sh .env.dev -p whatsapp_miner_dev -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up --build

dev-local-detached:
	@echo "🚀 Starting dev environment locally (background)..."
	@echo "📝 Updating .env.dev from Doppler..."
	@doppler secrets download --project whatsapp_miner_backend --config dev --format docker --no-file --silent > .env.dev
	@./scripts/docker-compose-with-env.sh .env.dev -p whatsapp_miner_dev -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d --build
	@echo "✓ Dev environment started"

# ────────────────────────────────────────────────────────────────────────────
# Local Production Testing
# ────────────────────────────────────────────────────────────────────────────

prod-local:
	@echo "🚀 Starting prod environment locally..."
	@echo "📝 Updating .env.prod from Doppler..."
	@doppler secrets download --project whatsapp_miner_backend --config prd --format docker --no-file --silent > .env.prod
	@./scripts/docker-compose-with-env.sh .env.prod -p whatsapp_miner_prod -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up --build

prod-local-detached:
	@echo "🚀 Starting prod environment locally (background)..."
	@echo "📝 Updating .env.prod from Doppler..."
	@doppler secrets download --project whatsapp_miner_backend --config prd --format docker --no-file --silent > .env.prod
	@./scripts/docker-compose-with-env.sh .env.prod -p whatsapp_miner_prod -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d --build
	@echo "✓ Prod environment started"

# ────────────────────────────────────────────────────────────────────────────
# Local Staging Testing
# ────────────────────────────────────────────────────────────────────────────

stg-local:
	@echo "🚀 Starting stg environment locally..."
	@echo "📝 Updating .env.stg from Doppler..."
	@doppler secrets download --project whatsapp_miner_backend --config stg --format docker --no-file --silent > .env.stg
	@./scripts/docker-compose-with-env.sh .env.stg -p whatsapp_miner_stg -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up --build

stg-local-detached:
	@echo "🚀 Starting stg environment locally (background)..."
	@echo "📝 Updating .env.stg from Doppler..."
	@doppler secrets download --project whatsapp_miner_backend --config stg --format docker --no-file --silent > .env.stg
	@./scripts/docker-compose-with-env.sh .env.stg -p whatsapp_miner_stg -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d --build
	@echo "✓ Stg environment started"

# ────────────────────────────────────────────────────────────────────────────
# Remote Deployment Testing with act
# ────────────────────────────────────────────────────────────────────────────

stg-deploy: sync-secrets
	@echo "🧪 Testing stg deployment with act..."
	@act workflow_dispatch \
		-W .github/workflows/deploy.yml \
		--secret-file .env.stg \
		--input environment=stg \
		--container-daemon-socket /var/run/docker.sock \
		--container-options "--group-add $(shell getent group docker | cut -d: -f3)"

prod-deploy: sync-secrets
	@echo "🧪 Testing prod deployment with act..."
	@act workflow_dispatch \
		-W .github/workflows/deploy.yml \
		--secret-file .env.prod \
		--input environment=prod \
		--container-daemon-socket /var/run/docker.sock \
		--container-options "--group-add $(shell getent group docker | cut -d: -f3)"

# ────────────────────────────────────────────────────────────────────────────
# Secret Management
# ────────────────────────────────────────────────────────────────────────────

sync-secrets:
	@echo "🔐 Syncing secrets from Doppler..."
	@doppler secrets download --project whatsapp_miner_backend --config dev --format docker --no-file --silent > .env.dev
	@doppler secrets download --project whatsapp_miner_backend --config stg --format docker --no-file --silent > .env.stg
	@doppler secrets download --project whatsapp_miner_backend --config prd --format docker --no-file --silent > .env.prod
	@echo "✓ Secrets synced to .env.dev, .env.stg, and .env.prod"

generate-env-example:
	@echo "📝 Generating .env.example from Doppler..."
	@doppler secrets download --project whatsapp_miner_backend --config dev --format env \
		| sed 's/=.*/=/' > .env.example
	@echo "✓ .env.example generated (values removed for template)"

# ────────────────────────────────────────────────────────────────────────────
# Health Checks
# ────────────────────────────────────────────────────────────────────────────

health-local:
	@echo "🏥 Checking local container health (works for dev and prod)..."
	@docker ps --filter "name=whatsapp_miner" --format "table {{.Names}}\t{{.Status}}" | grep -E "NAMES|whatsapp_miner" || echo "No containers running"

health-local-dev:
	@echo "🏥 Checking dev container health..."
	@docker ps --filter "name=whatsapp_miner.*_dev" --format "table {{.Names}}\t{{.Status}}" | grep -E "NAMES|whatsapp_miner.*_dev" || echo "No dev containers running"

health-local-stg:
	@echo "🏥 Checking stg container health..."
	@docker ps --filter "name=whatsapp_miner.*_stg" --format "table {{.Names}}\t{{.Status}}" | grep -E "NAMES|whatsapp_miner.*_stg" || echo "No stg containers running"

health-local-prod:
	@echo "🏥 Checking prod container health..."
	@docker ps --filter "name=whatsapp_miner.*_prod" --format "table {{.Names}}\t{{.Status}}" | grep -E "NAMES|whatsapp_miner.*_prod" || echo "No prod containers running"

health-remote-stg:
	@echo "🏥 Checking health on stg EC2..."
	@doppler run --project whatsapp_miner_backend --config stg --command '\
		echo "$$AWS_EC2_PEM_CHATBOT_SA_B64" | base64 -d > /tmp/temp_key.pem && \
		chmod 400 /tmp/temp_key.pem && \
		trap "rm -f /tmp/temp_key.pem" EXIT && \
		ssh -i /tmp/temp_key.pem ubuntu@$$AWS_EC2_HOST_ADDRESS \
			"docker ps --filter \"name=whatsapp_miner.*_stg\" --format \"table {{.Names}}\t{{.Status}}\""'

health-remote-prod:
	@echo "🏥 Checking health on prod EC2..."
	@doppler run --project whatsapp_miner_backend --config prd --command '\
		echo "$$AWS_EC2_PEM_CHATBOT_SA_B64" | base64 -d > /tmp/temp_key.pem && \
		chmod 400 /tmp/temp_key.pem && \
		trap "rm -f /tmp/temp_key.pem" EXIT && \
		ssh -i /tmp/temp_key.pem ubuntu@$$AWS_EC2_HOST_ADDRESS \
			"docker ps --filter \"name=whatsapp_miner.*_prod\" --format \"table {{.Names}}\t{{.Status}}\""'

# ────────────────────────────────────────────────────────────────────────────
# Remote Access
# ────────────────────────────────────────────────────────────────────────────

ssh-stage:
	@echo "🔐 Connecting to stage EC2..."
	@doppler run --project whatsapp_miner_backend --config stg --command '\
		echo "$$AWS_EC2_PEM_CHATBOT_SA_B64" | base64 -d > /tmp/temp_key.pem && \
		chmod 400 /tmp/temp_key.pem && \
		trap "rm -f /tmp/temp_key.pem" EXIT && \
		ssh -i /tmp/temp_key.pem ubuntu@$$AWS_EC2_HOST_ADDRESS'

ssh-prod:
	@echo "🔐 Connecting to prod EC2..."
	@doppler run --project whatsapp_miner_backend --config prd --command '\
		echo "$$AWS_EC2_PEM_CHATBOT_SA_B64" | base64 -d > /tmp/temp_key.pem && \
		chmod 400 /tmp/temp_key.pem && \
		trap "rm -f /tmp/temp_key.pem" EXIT && \
		ssh -i /tmp/temp_key.pem ubuntu@$$AWS_EC2_HOST_ADDRESS'

# ────────────────────────────────────────────────────────────────────────────
# Database Access
# ────────────────────────────────────────────────────────────────────────────

psql-dev:
	@echo "🐘 Connecting to dev database..."
	@doppler run --project whatsapp_miner_backend --config dev --command 'PGPASSWORD="$$SUPABASE_DATABASE_PASSWORD" $$SUPABASE_PSQL_COMMAND'

psql-stage:
	@echo "🐘 Connecting to stage database..."
	@doppler run --project whatsapp_miner_backend --config stg --command 'PGPASSWORD="$$SUPABASE_DATABASE_PASSWORD" $$SUPABASE_PSQL_COMMAND'

psql-prod:
	@echo "🐘 Connecting to prod database..."
	@doppler run --project whatsapp_miner_backend --config prd --command 'PGPASSWORD="$$SUPABASE_DATABASE_PASSWORD" $$SUPABASE_PSQL_COMMAND'

# ────────────────────────────────────────────────────────────────────────────
# Database Migrations
# ────────────────────────────────────────────────────────────────────────────

run-migrations-dev:
	@echo "🔄 Running migrations for dev environment..."
	@doppler run --project whatsapp_miner_backend --config dev --command 'cd /home/noams/src/whatsapp_miner && poetry shell && poetry run alembic upgrade head'

run-migrations-stage:
	@echo "🔄 Running migrations for stage environment..."
	@doppler run --project whatsapp_miner_backend --config stg --command 'cd /home/noams/src/whatsapp_miner && poetry shell && poetry run alembic upgrade head'

run-migrations-prod:
	@echo "🔄 Running migrations for prod environment..."
	@doppler run --project whatsapp_miner_backend --config prd --command 'cd /home/noams/src/whatsapp_miner && poetry shell && poetry run alembic upgrade head'

# ────────────────────────────────────────────────────────────────────────────
# Utilities
# ────────────────────────────────────────────────────────────────────────────

clean:
	@echo "🧹 Cleaning up containers and volumes..."
	@docker compose -p whatsapp_miner_dev -f docker/docker-compose.yml -f docker/docker-compose.dev.yml down -v 2>/dev/null || true
	@docker compose -p whatsapp_miner_stg -f docker/docker-compose.yml -f docker/docker-compose.prod.yml down -v 2>/dev/null || true
	@docker compose -p whatsapp_miner_prod -f docker/docker-compose.yml -f docker/docker-compose.prod.yml down -v 2>/dev/null || true
	@echo "✓ Cleanup complete"

logs:
	@echo "📋 Showing logs for all projects..."
	@echo "Dev logs:"
	@docker compose -p whatsapp_miner_dev -f docker/docker-compose.yml logs --tail 10 2>/dev/null || echo "No dev containers running"
	@echo ""
	@echo "Stg logs:"
	@docker compose -p whatsapp_miner_stg -f docker/docker-compose.yml logs --tail 10 2>/dev/null || echo "No stg containers running"
	@echo ""
	@echo "Prod logs:"
	@docker compose -p whatsapp_miner_prod -f docker/docker-compose.yml logs --tail 10 2>/dev/null || echo "No prod containers running"

logs-dev:
	@docker compose -p whatsapp_miner_dev -f docker/docker-compose.yml logs -f

logs-stg:
	@docker compose -p whatsapp_miner_stg -f docker/docker-compose.yml logs -f

logs-prod:
	@docker compose -p whatsapp_miner_prod -f docker/docker-compose.yml logs -f

logs-miner-dev:
	@docker compose -p whatsapp_miner_dev -f docker/docker-compose.yml logs -f miner

logs-miner-stg:
	@docker compose -p whatsapp_miner_stg -f docker/docker-compose.yml logs -f miner

logs-miner-prod:
	@docker compose -p whatsapp_miner_prod -f docker/docker-compose.yml logs -f miner

logs-classifier-dev:
	@docker compose -p whatsapp_miner_dev -f docker/docker-compose.yml logs -f classifier

logs-classifier-stg:
	@docker compose -p whatsapp_miner_stg -f docker/docker-compose.yml logs -f classifier

logs-classifier-prod:
	@docker compose -p whatsapp_miner_prod -f docker/docker-compose.yml logs -f classifier

shell-miner-dev:
	@docker compose -p whatsapp_miner_dev -f docker/docker-compose.yml exec miner bash

shell-miner-prod:
	@docker compose -p whatsapp_miner_prod -f docker/docker-compose.yml exec miner bash

shell-miner-stg:
	@docker compose -p whatsapp_miner_stg -f docker/docker-compose.yml exec miner bash

shell-classifier-dev:
	@docker compose -p whatsapp_miner_dev -f docker/docker-compose.yml exec classifier bash

shell-classifier-prod:
	@docker compose -p whatsapp_miner_prod -f docker/docker-compose.yml exec classifier bash

shell-classifier-stg:
	@docker compose -p whatsapp_miner_stg -f docker/docker-compose.yml exec classifier bash

ps:
	@echo "📊 Container status:"
	@echo "Dev containers:"
	@docker ps --filter "name=whatsapp_miner.*_dev" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "No dev containers"
	@echo ""
	@echo "Stg containers:"
	@docker ps --filter "name=whatsapp_miner.*_stg" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "No stg containers"
	@echo ""
	@echo "Prod containers:"
	@docker ps --filter "name=whatsapp_miner.*_prod" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "No prod containers"

restart-dev:
	@echo "🔄 Restarting dev services..."
	@docker compose -p whatsapp_miner_dev -f docker/docker-compose.yml restart

restart-stg:
	@echo "🔄 Restarting stg services..."
	@docker compose -p whatsapp_miner_stg -f docker/docker-compose.yml restart

restart-prod:
	@echo "🔄 Restarting prod services..."
	@docker compose -p whatsapp_miner_prod -f docker/docker-compose.yml restart

stop-dev:
	@echo "🛑 Stopping dev services..."
	@docker compose -p whatsapp_miner_dev -f docker/docker-compose.yml stop

stop-stg:
	@echo "🛑 Stopping stg services..."
	@docker compose -p whatsapp_miner_stg -f docker/docker-compose.yml stop

stop-prod:
	@echo "🛑 Stopping prod services..."
	@docker compose -p whatsapp_miner_prod -f docker/docker-compose.yml stop


# ────────────────────────────────────────────────────────────────────────────
# Help
# ────────────────────────────────────────────────────────────────────────────

help:
	@echo "════════════════════════════════════════════════════════════════════"
	@echo "WhatsApp Miner - Available Commands"
	@echo "════════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Local Development:"
	@echo "  make dev-local              - Start dev environment locally"
	@echo "  make dev-local-detached     - Start dev environment locally (background)"
	@echo "  make stg-local              - Start stg environment locally"
	@echo "  make stg-local-detached     - Start stg environment locally (background)"
	@echo "  make prod-local             - Start prod environment locally"
	@echo "  make prod-local-detached    - Start prod environment locally (background)"
	@echo ""
	@echo "Remote Deployment Testing:"
	@echo "  make stg-deploy             - Test staging deployment with act"
	@echo "  make prod-deploy            - Test prod deployment with act"
	@echo ""
	@echo "Health Checks:"
	@echo "  make health-local           - Check all local container health"
	@echo "  make health-local-dev       - Check dev container health"
	@echo "  make health-local-stg       - Check stg container health"
	@echo "  make health-local-prod      - Check prod container health"
	@echo "  make health-remote-stg      - Check stg EC2 container health"
	@echo "  make health-remote-prod     - Check prod EC2 container health"
	@echo ""
	@echo "Remote Access:"
	@echo "  make ssh-stage              - SSH into stage EC2 instance"
	@echo "  make ssh-prod               - SSH into prod EC2 instance"
	@echo ""
	@echo "Database Access:"
	@echo "  make psql-dev               - Connect to dev database"
	@echo "  make psql-stage             - Connect to stage database"
	@echo "  make psql-prod              - Connect to prod database"
	@echo ""
	@echo "Database Migrations:"
	@echo "  make run-migrations-dev     - Run migrations for dev environment"
	@echo "  make run-migrations-stage   - Run migrations for stage environment"
	@echo "  make run-migrations-prod    - Run migrations for prod environment"
	@echo ""
	@echo "Secrets:"
	@echo "  make sync-secrets           - Update .env files from Doppler"
	@echo "  make generate-env-example   - Generate .env.example template"
	@echo ""
	@echo "Logs:"
	@echo "  make logs                   - Show logs for all projects"
	@echo "  make logs-dev               - Tail dev service logs"
	@echo "  make logs-stg               - Tail stg service logs"
	@echo "  make logs-prod              - Tail prod service logs"
	@echo "  make logs-miner-dev         - Tail dev miner logs"
	@echo "  make logs-miner-stg         - Tail stg miner logs"
	@echo "  make logs-miner-prod        - Tail prod miner logs"
	@echo "  make logs-classifier-dev    - Tail dev classifier logs"
	@echo "  make logs-classifier-stg    - Tail stg classifier logs"
	@echo "  make logs-classifier-prod   - Tail prod classifier logs"
	@echo ""
	@echo "Utilities:"
	@echo "  make ps                     - Show container status for all projects"
	@echo "  make shell-miner-dev        - Shell into dev miner container"
	@echo "  make shell-miner-stg        - Shell into stg miner container"
	@echo "  make shell-miner-prod       - Shell into prod miner container"
	@echo "  make shell-classifier-dev   - Shell into dev classifier container"
	@echo "  make shell-classifier-stg   - Shell into stg classifier container"
	@echo "  make shell-classifier-prod  - Shell into prod classifier container"
	@echo "  make restart-dev            - Restart dev services"
	@echo "  make restart-stg            - Restart stg services"
	@echo "  make restart-prod           - Restart prod services"
	@echo "  make stop-dev               - Stop dev services"
	@echo "  make stop-stg               - Stop stg services"
	@echo "  make stop-prod              - Stop prod services"
	@echo "  make clean                  - Remove all containers and volumes"
	@echo "  make help                   - Show this help message"
	@echo ""
	@echo "════════════════════════════════════════════════════════════════════"

