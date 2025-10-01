.PHONY: dev prod-local test-deploy test-deploy-prod sync-secrets clean logs shell-miner shell-classifier help

# ════════════════════════════════════════════════════════════════════════════
# WhatsApp Miner - Makefile
# ════════════════════════════════════════════════════════════════════════════

# ────────────────────────────────────────────────────────────────────────────
# Local Development (daily use)
# ────────────────────────────────────────────────────────────────────────────

dev:
	@echo "🚀 Starting dev environment with Doppler..."
	@echo "📝 Writing secrets to .env..."
	@doppler secrets download --project whatsapp_miner_backend --config dev_personal --format docker --no-file --silent > .env
	@ENV_FILE=$$(pwd)/.env ./scripts/load-env-and-run.sh .env -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up --build
	@rm -f .env

dev-detached:
	@echo "🚀 Starting dev environment in background..."
	@echo "📝 Writing secrets to .env..."
	@doppler secrets download --project whatsapp_miner_backend --config dev_personal --format docker --no-file --silent > .env
	@ENV_FILE=$$(pwd)/.env ./scripts/load-env-and-run.sh .env -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d --build
	@echo "✓ Secrets written and containers started"

# ────────────────────────────────────────────────────────────────────────────
# Production Testing Locally
# ────────────────────────────────────────────────────────────────────────────

prod-local: sync-secrets
	@echo "🚀 Starting production config locally..."
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml --env-file .env.prod up --build

prod-local-detached: sync-secrets
	@echo "🚀 Starting production config in background..."
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml --env-file .env.prod up -d --build

# ────────────────────────────────────────────────────────────────────────────
# CI/CD Testing with act
# ────────────────────────────────────────────────────────────────────────────

test-deploy: sync-secrets
	@echo "🧪 Testing deploy workflow with act (dev config)..."
	act workflow_dispatch -W .github/workflows/deploy.yml --secret-file .secrets.dev

test-deploy-prod: sync-secrets
	@echo "🧪 Testing deploy workflow with act (prod config)..."
	act workflow_dispatch -W .github/workflows/deploy.yml --secret-file .secrets.prod

# ────────────────────────────────────────────────────────────────────────────
# Secret Management
# ────────────────────────────────────────────────────────────────────────────

sync-secrets:
	@echo "🔐 Syncing secrets from Doppler..."
	@doppler secrets download --project whatsapp_miner_backend --config dev_personal --format env --no-file --silent | sed 's/="\(.*\)"/=\1/' > .env.local
	@doppler secrets download --project whatsapp_miner_backend --config dev_personal --format env --no-file --silent | sed 's/="\(.*\)"/=\1/' > .secrets.dev
	@doppler secrets download --project whatsapp_miner_backend --config prd --format env --no-file --silent | sed 's/="\(.*\)"/=\1/' > .env.prod
	@doppler secrets download --project whatsapp_miner_backend --config prd --format env --no-file --silent | sed 's/="\(.*\)"/=\1/' > .secrets.prod
	@echo "✓ Secrets synced to .env.local, .env.prod, .secrets.dev, .secrets.prod"

generate-env-example:
	@echo "📝 Generating .env.example from Doppler..."
	@doppler secrets download --project whatsapp_miner_backend --config dev_personal --format env \
		| sed 's/=.*/=/' > .env.example
	@echo "✓ .env.example generated (values removed for template)"

# ────────────────────────────────────────────────────────────────────────────
# Health Checks
# ────────────────────────────────────────────────────────────────────────────

health:
	@echo "🏥 Checking service health..."
	@echo -n "Miner (port 8000): "
	@curl -sf http://localhost:8000/health && echo "✅ Healthy" || echo "❌ Unhealthy"
	@echo -n "Classifier (port 8001): "
	@curl -sf http://localhost:8001/health && echo "✅ Healthy" || echo "❌ Unhealthy"

health-wait:
	@echo "⏳ Waiting for services to become healthy..."
	@timeout 120 bash -c 'until curl -sf http://localhost:8000/health >/dev/null 2>&1; do sleep 2; echo -n "."; done' && echo " Miner ready ✅"
	@timeout 120 bash -c 'until curl -sf http://localhost:8001/health >/dev/null 2>&1; do sleep 2; echo -n "."; done' && echo " Classifier ready ✅"
	@echo "🎉 All services healthy!"

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
	@echo "Development:"
	@echo "  make dev              - Start dev environment (live Doppler secrets)"
	@echo "  make dev-detached     - Start dev environment in background"
	@echo "  make prod-local       - Test production config locally"
	@echo ""
	@echo "CI/CD Testing:"
	@echo "  make test-deploy      - Test deploy workflow locally (dev)"
	@echo "  make test-deploy-prod - Test deploy workflow locally (prod)"
	@echo ""
	@echo "Health Checks:"
	@echo "  make health           - Check if services are healthy"
	@echo "  make health-wait      - Wait for services to become healthy"
	@echo ""
	@echo "Secrets:"
	@echo "  make sync-secrets     - Sync all secrets from Doppler"
	@echo "  make generate-env-example - Generate .env.example template"
	@echo ""
	@echo "Logs:"
	@echo "  make logs             - Tail all service logs"
	@echo "  make logs-miner       - Tail miner logs"
	@echo "  make logs-classifier  - Tail classifier logs"
	@echo "  make logs-migrate     - Show migration logs"
	@echo ""
	@echo "Utilities:"
	@echo "  make ps               - Show container status"
	@echo "  make shell-miner      - Shell into miner container"
	@echo "  make shell-classifier - Shell into classifier container"
	@echo "  make restart          - Restart all services"
	@echo "  make stop             - Stop all services"
	@echo "  make clean            - Remove all containers and volumes"
	@echo "  make help             - Show this help message"
	@echo ""
	@echo "════════════════════════════════════════════════════════════════════"

