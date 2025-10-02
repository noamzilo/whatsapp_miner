.PHONY: dev-local dev-local-detached prod-local prod-local-detached dev-deploy prod-deploy sync-secrets clean logs shell-miner shell-classifier help

# ════════════════════════════════════════════════════════════════════════════
# WhatsApp Miner - Makefile
# ════════════════════════════════════════════════════════════════════════════

# ────────────────────────────────────────────────────────────────────────────
# Local Development (daily use)
# ────────────────────────────────────────────────────────────────────────────

dev-local:
	@echo "🚀 Starting dev environment locally..."
	@echo "📝 Updating .env.dev from Doppler..."
	@doppler secrets download --project whatsapp_miner_backend --config dev_personal --format docker --no-file --silent > .env.dev
	@./scripts/docker-compose-with-env.sh .env.dev -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up --build

dev-local-detached:
	@echo "🚀 Starting dev environment locally (background)..."
	@echo "📝 Updating .env.dev from Doppler..."
	@doppler secrets download --project whatsapp_miner_backend --config dev_personal --format docker --no-file --silent > .env.dev
	@./scripts/docker-compose-with-env.sh .env.dev -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d --build
	@echo "✓ Dev environment started"

# ────────────────────────────────────────────────────────────────────────────
# Local Production Testing
# ────────────────────────────────────────────────────────────────────────────

prod-local:
	@echo "🚀 Starting prod environment locally..."
	@echo "📝 Updating .env.prod from Doppler..."
	@doppler secrets download --project whatsapp_miner_backend --config prd --format docker --no-file --silent > .env.prod
	@./scripts/docker-compose-with-env.sh .env.prod -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up --build

prod-local-detached:
	@echo "🚀 Starting prod environment locally (background)..."
	@echo "📝 Updating .env.prod from Doppler..."
	@doppler secrets download --project whatsapp_miner_backend --config prd --format docker --no-file --silent > .env.prod
	@./scripts/docker-compose-with-env.sh .env.prod -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d --build
	@echo "✓ Prod environment started"

# ────────────────────────────────────────────────────────────────────────────
# Remote Deployment Testing with act
# ────────────────────────────────────────────────────────────────────────────

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
	@doppler secrets download --project whatsapp_miner_backend --config dev_personal --format docker --no-file --silent > .env.dev
	@doppler secrets download --project whatsapp_miner_backend --config prd --format docker --no-file --silent > .env.prod
	@echo "✓ Secrets synced to .env.dev and .env.prod"

generate-env-example:
	@echo "📝 Generating .env.example from Doppler..."
	@doppler secrets download --project whatsapp_miner_backend --config dev_personal --format env \
		| sed 's/=.*/=/' > .env.example
	@echo "✓ .env.example generated (values removed for template)"

# ────────────────────────────────────────────────────────────────────────────
# Health Checks
# ────────────────────────────────────────────────────────────────────────────

health:
	@echo "🏥 Checking local container health (works for dev and prod)..."
	@docker ps --filter "name=whatsapp_miner" --format "table {{.Names}}\t{{.Status}}" | grep -E "NAMES|whatsapp_miner" || echo "No containers running"

health-remote-dev:
	@echo "🏥 Checking health on dev EC2..."
	@doppler run --project whatsapp_miner_backend --config dev_personal --command '\
		echo "$$AWS_EC2_PEM_CHATBOT_SA_B64" | base64 -d > /tmp/temp_key.pem && \
		chmod 400 /tmp/temp_key.pem && \
		trap "rm -f /tmp/temp_key.pem" EXIT && \
		ssh -i /tmp/temp_key.pem ubuntu@$$AWS_EC2_HOST_ADDRESS \
			"docker ps --filter \"name=whatsapp_miner\" --format \"table {{.Names}}\t{{.Status}}\""'

health-remote-prod:
	@echo "🏥 Checking health on prod EC2..."
	@doppler run --project whatsapp_miner_backend --config prd --command '\
		echo "$$AWS_EC2_PEM_CHATBOT_SA_B64" | base64 -d > /tmp/temp_key.pem && \
		chmod 400 /tmp/temp_key.pem && \
		trap "rm -f /tmp/temp_key.pem" EXIT && \
		ssh -i /tmp/temp_key.pem ubuntu@$$AWS_EC2_HOST_ADDRESS \
			"docker ps --filter \"name=whatsapp_miner\" --format \"table {{.Names}}\t{{.Status}}\""'

# ────────────────────────────────────────────────────────────────────────────
# Remote Access
# ────────────────────────────────────────────────────────────────────────────

ssh-dev:
	@echo "🔐 Connecting to dev EC2..."
	@doppler run --project whatsapp_miner_backend --config dev_personal --command '\
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
# Utilities
# ────────────────────────────────────────────────────────────────────────────

clean:
	@echo "🧹 Cleaning up containers and volumes..."
	@docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml down -v 2>/dev/null || true
	@docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml down -v 2>/dev/null || true
	@echo "✓ Cleanup complete"

logs:
	@docker compose -f docker/docker-compose.yml logs -f

logs-miner:
	@docker compose -f docker/docker-compose.yml logs -f miner

logs-classifier:
	@docker compose -f docker/docker-compose.yml logs -f classifier

logs-migrate:
	@docker compose -f docker/docker-compose.yml logs migrate

shell-miner:
	@docker compose -f docker/docker-compose.yml exec miner bash

shell-classifier:
	@docker compose -f docker/docker-compose.yml exec classifier bash

ps:
	@echo "📊 Container status:"
	@docker compose -f docker/docker-compose.yml ps

restart:
	@echo "🔄 Restarting services..."
	@docker compose -f docker/docker-compose.yml restart

stop:
	@echo "🛑 Stopping services..."
	@docker compose -f docker/docker-compose.yml stop

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
	@echo "  make prod-local             - Start prod environment locally"
	@echo "  make prod-local-detached    - Start prod environment locally (background)"
	@echo ""
	@echo "Remote Deployment Testing:"
	@echo "  make dev-deploy             - Test dev deployment with act"
	@echo "  make prod-deploy            - Test prod deployment with act"
	@echo ""
	@echo "Health Checks:"
	@echo "  make health                 - Check local container health status"
	@echo "  make health-remote-dev      - Check dev EC2 container health"
	@echo "  make health-remote-prod     - Check prod EC2 container health"
	@echo ""
	@echo "Remote Access:"
	@echo "  make ssh-dev                - SSH into dev EC2 instance"
	@echo "  make ssh-prod               - SSH into prod EC2 instance"
	@echo ""
	@echo "Secrets:"
	@echo "  make sync-secrets           - Update .env.dev and .env.prod from Doppler"
	@echo "  make generate-env-example   - Generate .env.example template"
	@echo ""
	@echo "Logs:"
	@echo "  make logs                   - Tail all service logs"
	@echo "  make logs-miner             - Tail miner logs"
	@echo "  make logs-classifier        - Tail classifier logs"
	@echo "  make logs-migrate           - Show migration logs"
	@echo ""
	@echo "Utilities:"
	@echo "  make ps                     - Show container status"
	@echo "  make shell-miner            - Shell into miner container"
	@echo "  make shell-classifier       - Shell into classifier container"
	@echo "  make restart                - Restart all services"
	@echo "  make stop                   - Stop all services"
	@echo "  make clean                  - Remove all containers and volumes"
	@echo "  make help                   - Show this help message"
	@echo ""
	@echo "════════════════════════════════════════════════════════════════════"

