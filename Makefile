.PHONY: dev-local stg-local prod-local stg-deploy prod-deploy sync-secrets-docker sync-secrets-env generate-env-example clean clean-local clean-local-dev clean-local-stg clean-local-prod clean-remote-stg clean-remote-prod health-local health-local-dev health-local-stg health-local-prod health-remote-stg health-remote-prod ssh-stage ssh-prod psql-dev psql-stage psql-prod run-migrations-dev run-migrations-stage run-migrations-prod logs logs-dev logs-stg logs-prod logs-miner-dev logs-miner-stg logs-miner-prod logs-classifier-dev logs-classifier-stg logs-classifier-prod docker-exec-miner-dev-local docker-exec-miner-stg-local docker-exec-miner-prod-local docker-exec-classifier-dev-local docker-exec-classifier-stg-local docker-exec-classifier-prod-local ps ps-local ps-remote restart-dev restart-stg restart-prod stop-dev stop-stg stop-prod cache-clear cache-clear-manual-classifier help

# ════════════════════════════════════════════════════════════════════════════
# WhatsApp Miner - Makefile
# ════════════════════════════════════════════════════════════════════════════

# ────────────────────────────────────────────────────────────────────────────
# Variables
# ────────────────────────────────────────────────────────────────────────────

# Project and container names
PROJECT_NAME := whatsapp_miner
MINER_CONTAINER := $(PROJECT_NAME)_miner
CLASSIFIER_CONTAINER := $(PROJECT_NAME)_classifier

# Environment configurations
ENVIRONMENTS := dev stg prod
ENV_CONFIGS := dev:dev stg:stg prod:prd

# Docker compose files
DOCKER_COMPOSE_BASE := docker/docker-compose.yml
DOCKER_COMPOSE_DEV := docker/docker-compose.dev.yml
DOCKER_COMPOSE_PROD := docker/docker-compose.prod.yml

# Common Doppler project
DOPPLER_PROJECT := whatsapp_miner_backend

# Global Python environment setup
export PYTHONPATH := $(shell pwd)
export WORKING_DIR := $(shell pwd)

# SSH key handling
SSH_KEY_SETUP := KEY_FILE="/tmp/temp_key_$$(date +%s).pem" && echo "$$AWS_EC2_PEM_CHATBOT_SA_B64" | base64 -d > "$$KEY_FILE" && chmod 600 "$$KEY_FILE" && trap "rm -f $$KEY_FILE" EXIT

# ────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ────────────────────────────────────────────────────────────────────────────

# Function to extract Doppler config name for environment
define extract_doppler_config
$(word 2,$(subst :, ,$(filter $(1):%,$(ENV_CONFIGS))))
endef

# Function to build project prefix for environment
define build_project_prefix
$(PROJECT_NAME)_$(1)
endef

# Function to build container names for environment
define build_container_names
$(MINER_CONTAINER)_$(1) $(CLASSIFIER_CONTAINER)_$(1)
endef

# Function to download environment secrets (parameterized format: docker|env)
define download_env_secrets
echo "📝 Updating .env.$(1) from Doppler (format=$(2))..."
doppler secrets download --project $(DOPPLER_PROJECT) --config $(call extract_doppler_config,$(1)) --format=$(2) --no-file --silent > .env.$(1)
endef

# Function to run docker compose with environment variables for local environment
# Parameters: $(1)=env, $(2)=docker compose command and args
define docker_compose_local
@$(eval _DOCKER_COMPOSE_OVERRIDE := $(if $(filter $(1),dev),$(DOCKER_COMPOSE_DEV),$(DOCKER_COMPOSE_PROD)))
@./scripts/docker-compose-with-env.sh .env.$(1) -p $(call build_project_prefix,$(1)) -f $(DOCKER_COMPOSE_BASE) -f $(_DOCKER_COMPOSE_OVERRIDE) $(2)
endef

# Function to run docker compose with environment variables for remote environment
# Parameters: $(1)=env, $(2)=docker compose command and args
define docker_compose_remote
@doppler run --project $(DOPPLER_PROJECT) --config $(call extract_doppler_config,$(1)) --command '\
	$(SSH_KEY_SETUP) && \
	ssh -i "$$KEY_FILE" ubuntu@$$AWS_EC2_HOST_ADDRESS \
		"cd $$AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER && \
		./scripts/docker-compose-with-env.sh .env.$(1) -p $(call build_project_prefix,$(1)) -f docker/docker-compose.yml -f docker/docker-compose.$(if $(filter $(1),dev),dev,prod).yml $(2)"'
endef

# Function to start environment locally (with optional detached mode and port overrides)
# Parameters: $(1)=env, $(2)=detached_flag, $(3)=miner_port, $(4)=classifier_port, $(5)=run_migrations
define start_env_local
@echo "🔧 Starting $(1) environment with params: detached='$(2)', miner_port='$(3)', classifier_port='$(4)', run_migrations='$(5)'"
$(call download_env_secrets,$(1),docker)
@# Pre-compute values to avoid complex shell expressions
@$(eval _RUN_MIGRATIONS := $(or $(5),$(RUN_MIGRATIONS)))
@$(eval _DOCKER_COMPOSE_OVERRIDE := $(if $(filter $(1),dev),$(DOCKER_COMPOSE_DEV),$(DOCKER_COMPOSE_PROD)))
@$(eval _DETACHED_FLAG := $(if $(2),-d))
@$(eval _SSH_MINER := $(if $(3),SSH_PORT_MINER=$(3)))
@$(eval _SSH_CLASSIFIER := $(if $(4),SSH_PORT_CLASSIFIER=$(4)))
@echo "🔧 Computed values: RUN_MIGRATIONS='$(_RUN_MIGRATIONS)', DOCKER_COMPOSE_OVERRIDE='$(_DOCKER_COMPOSE_OVERRIDE)', DETACHED_FLAG='$(_DETACHED_FLAG)'"
@echo "🔧 Executing: $(_SSH_MINER) $(_SSH_CLASSIFIER) RUN_MIGRATIONS=$(_RUN_MIGRATIONS) ./scripts/docker-compose-with-env.sh .env.$(1) -p $(call build_project_prefix,$(1)) -f $(DOCKER_COMPOSE_BASE) -f $(_DOCKER_COMPOSE_OVERRIDE) up $(_DETACHED_FLAG) --build"
@$(_SSH_MINER) $(_SSH_CLASSIFIER) RUN_MIGRATIONS=$(_RUN_MIGRATIONS) ./scripts/docker-compose-with-env.sh .env.$(1) -p $(call build_project_prefix,$(1)) -f $(DOCKER_COMPOSE_BASE) -f $(_DOCKER_COMPOSE_OVERRIDE) up $(_DETACHED_FLAG) --build || (echo "❌ ERROR: Command failed in start_env_local function for environment $(1)" && exit 1)
$(if $(2),@echo "✓ $(1) environment started$(if $(3), with SSH ports)")
endef


# Port schema: {project}{env}{container}
# Project: 1 (whatsapp_miner)
# Environment: 1 (dev), 2 (stg), 3 (prod)  
# Container: 1 (miner), 2 (classifier)

# Function to map environment name to number for port building
define map_env_to_number
$(if $(filter $(1),dev),1,$(if $(filter $(1),stg),2,3))
endef

# Function to build SSH port for container in environment
define build_ssh_port
1$(call map_env_to_number,$(1))$(2)
endef

# Function to build default SSH ports for environment (miner and classifier)
define build_default_ssh_ports
$(call build_ssh_port,$(1),1) $(call build_ssh_port,$(1),2)
endef

# Function to check local container health
define check_local_health
@echo "🏥 Checking $(1) container health..."
@$(call docker_compose_local,$(1),ps --format \"table {{.Name}}\t{{.Status}}\t{{.Service}}\") 2>/dev/null || echo "No $(1) containers running"
endef

# Function to check remote container health
define check_remote_health
@echo "🏥 Checking health on $(1) EC2..."
@$(call docker_compose_remote,$(1),"ps --format \"table {{.Name}}\t{{.Status}}\t{{.Service}}\"")
endef

# Function to SSH into environment
define ssh_env
@echo "🔐 Connecting to $(1) EC2..."
@doppler run --project $(DOPPLER_PROJECT) --config $(call extract_doppler_config,$(1)) --command '\
	$(SSH_KEY_SETUP) && \
	ssh -i "$$KEY_FILE" ubuntu@$$AWS_EC2_HOST_ADDRESS'
endef

# Function to connect to database
define psql_env
@echo "🐘 Connecting to $(1) database..."
@doppler run --project $(DOPPLER_PROJECT) --config $(call extract_doppler_config,$(1)) --command 'PGPASSWORD="$$SUPABASE_DATABASE_PASSWORD" $$SUPABASE_PSQL_COMMAND'
endef

# Function to run migrations
define run_migrations_env
@echo "🔄 Running migrations for $(1) environment..."
@doppler run --project $(DOPPLER_PROJECT) --config $(call extract_doppler_config,$(1)) --command 'cd /home/noams/src/whatsapp_miner && poetry shell && poetry run alembic upgrade head'
endef

# Function to clean local containers for environment
define clean_local_env
@echo "Stopping and removing $(1) containers and volumes..."
@$(call docker_compose_local,$(1),down -v --remove-orphans) 2>/dev/null || true
@echo "✓ $(1) environment cleaned up"
endef

# Function to clean remote containers for environment
define clean_remote_env
@echo "🧹 Cleaning up $(1) containers and volumes on remote EC2..."
@doppler run --project $(DOPPLER_PROJECT) --config $(call extract_doppler_config,$(1)) --command '\
	$(SSH_KEY_SETUP) && \
	ssh -i "$$KEY_FILE" ubuntu@$$AWS_EC2_HOST_ADDRESS \
		"cd $$AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER && \
		echo \"Stopping and removing $(1) containers and volumes...\" && \
		./scripts/docker-compose-with-env.sh .env.$(1) -p $(call build_project_prefix,$(1)) -f docker/docker-compose.yml -f docker/docker-compose.$(if $(filter $(1),dev),dev,prod).yml down -v --remove-orphans 2>/dev/null || true && \
		echo \"Cleaning up unused volumes...\" && \
		docker volume prune -f 2>/dev/null || true && \
		echo \"✓ $(1) cleanup complete\""'
endef

# Function to show logs for environment
define show_logs_env
@echo "$(1) logs:"
@$(call docker_compose_local,$(1),logs --tail 10) 2>/dev/null || echo "No $(1) containers running"
endef

# Function to tail logs for environment
define tail_logs_env
@$(call docker_compose_local,$(1),logs -f)
endef

# Function to tail logs for specific service in environment
define tail_logs_service_env
@$(call docker_compose_local,$(1),logs -f $(2))
endef

# Function to exec into container
define docker_exec_env
@$(call docker_compose_local,$(1),exec $(2) bash)
endef

# Function to show container status for environment
define show_container_status_env
@echo "$(1) containers:"
@$(call docker_compose_local,$(1),ps --format \"table {{.Name}}\t{{.Status}}\t{{.Ports}}\t{{.Service}}\") 2>/dev/null || echo "No $(1) containers"
endef

# Function to show remote container status
define show_remote_status_env
@echo "$(1) containers on EC2:"
@$(call docker_compose_remote,$(1),"ps --format \"table {{.Name}}\t{{.Status}}\t{{.Ports}}\t{{.Service}}\"") 2>/dev/null || echo "No $(1) containers on remote"
endef

# Function to restart environment
define restart_env
@echo "🔄 Restarting $(1) services..."
@$(call docker_compose_local,$(1),restart)
endef

# Function to stop environment
define stop_env
@echo "🛑 Stopping $(1) services..."
@$(call docker_compose_local,$(1),stop)
endef

# Function to test deployment with act
define test_deploy_env
@echo "🧪 Testing $(1) deployment with act..."
@act workflow_dispatch \
	-W .github/workflows/deploy.yml \
	--secret-file .env.$(1) \
	--input environment=$(1) \
	--container-daemon-socket /var/run/docker.sock \
	--container-options "--group-add $(shell getent group docker | cut -d: -f3)"
endef

# Function to generate help section for environment commands
define help_env_section
	@echo "  make $(1)-local              - Start $(1) environment locally (detached by default)"
	$(if $(filter $(1),dev),@echo "                               Args: PORTS=911,912 or MINER_PORT=... CLASSIFIER_PORT=... DETACHED=true|false")
@echo "  make clean-local-$(1)        - Clean $(1) containers and volumes"
@echo "  make health-local-$(1)       - Check $(1) container health"
@echo "  make health-remote-$(1)      - Check $(1) EC2 container health"
@echo "  make psql-$(1)               - Connect to $(1) database"
@echo "  make run-migrations-$(1)     - Run migrations for $(1) environment"
@echo "  make logs-$(1)               - Tail $(1) service logs"
@echo "  make logs-miner-$(1)         - Tail $(1) miner logs"
@echo "  make logs-classifier-$(1)    - Tail $(1) classifier logs"
@echo "  make docker-exec-miner-$(1)-local     - Shell into $(1) miner container"
@echo "  make docker-exec-classifier-$(1)-local - Shell into $(1) classifier container"
@echo "  make restart-$(1)            - Restart $(1) services"
@echo "  make stop-$(1)               - Stop $(1) services"
@echo "  make clean-remote-$(1)       - Clean $(1) containers on remote EC2"
endef

# Function to echo start message
define echo_start_env
@echo "🚀 Starting $(1) environment locally$(if $(2), $(2))..."
endef

# ────────────────────────────────────────────────────────────────────────────
# Local Development (daily use)
# ────────────────────────────────────────────────────────────────────────────

dev-local:
	@echo "🚀 Starting dev environment (detached by default)..."
	@echo "Args: PORTS=911,912 (or MINER_PORT / CLASSIFIER_PORT), DETACHED=true|false, RUN_MIGRATIONS=true|false"
	@# Derive ports: prefer explicit MINER_PORT/CLASSIFIER_PORT, else PORTS, else defaults
	@$(eval _PORTS_LIST := $(subst , ,$(strip $(PORTS))))
	@$(eval MINER_PORT := $(or $(MINER_PORT),$(word 1,$(_PORTS_LIST)),911))
	@$(eval CLASSIFIER_PORT := $(or $(CLASSIFIER_PORT),$(word 2,$(_PORTS_LIST)),912))
	@# Detached default true; pass flag accordingly
	@$(eval DETACHED := $(or $(DETACHED),true))
	@# RUN_MIGRATIONS default true for dev
	@$(eval RUN_MIGRATIONS := $(or $(RUN_MIGRATIONS),true))
	@echo "🔍 Debug: MINER_PORT='$(MINER_PORT)', CLASSIFIER_PORT='$(CLASSIFIER_PORT)', DETACHED='$(DETACHED)', RUN_MIGRATIONS='$(RUN_MIGRATIONS)'"
	$(call start_env_local,dev,$(if $(filter $(DETACHED),true),detached),$(MINER_PORT),$(CLASSIFIER_PORT),$(RUN_MIGRATIONS))

# ────────────────────────────────────────────────────────────────────────────
# Local Production Testing
# ────────────────────────────────────────────────────────────────────────────

prod-local:
	$(call echo_start_env,prod,(background))
	@# RUN_MIGRATIONS default false for prod
	@$(eval RUN_MIGRATIONS := $(or $(RUN_MIGRATIONS),false))
	$(call start_env_local,prod,detached,,,$(RUN_MIGRATIONS))


# ────────────────────────────────────────────────────────────────────────────
# Local Staging Testing
# ────────────────────────────────────────────────────────────────────────────

stg-local:
	$(call echo_start_env,stg,(background))
	@# RUN_MIGRATIONS default false for stg
	@$(eval RUN_MIGRATIONS := $(or $(RUN_MIGRATIONS),false))
	$(call start_env_local,stg,detached,,,$(RUN_MIGRATIONS))


# ────────────────────────────────────────────────────────────────────────────
# Remote Deployment Testing with act
# ────────────────────────────────────────────────────────────────────────────

stg-deploy: sync-secrets-docker
	$(call test_deploy_env,stg)

prod-deploy: sync-secrets-docker
	$(call test_deploy_env,prod)

# ────────────────────────────────────────────────────────────────────────────
# Secret Management
# ────────────────────────────────────────────────────────────────────────────

sync-secrets-docker:
	@echo "🔐 Syncing secrets from Doppler (docker format)..."
	$(foreach env,$(ENVIRONMENTS),$(call download_env_secrets,$(env),docker);)
	@echo "✓ Secrets (docker format) synced to .env.dev, .env.stg, and .env.prod"

sync-secrets-env:
	@echo "🔐 Syncing secrets from Doppler (env format)..."
	$(foreach env,$(ENVIRONMENTS),$(call download_env_secrets,$(env),env);)
	@echo "✓ Secrets (env format) synced to .env.dev, .env.stg, and .env.prod"

generate-env-example:
	@echo "📝 Generating .env.example from Doppler..."
	@doppler secrets download --project $(DOPPLER_PROJECT) --config dev --format env \
		| sed 's/=.*/=/' > .env.example
	@echo "✓ .env.example generated (values removed for template)"

# ────────────────────────────────────────────────────────────────────────────
# Health Checks
# ────────────────────────────────────────────────────────────────────────────

health-local:
	@echo "🏥 Checking local container health (works for dev and prod)..."
	@echo "Dev environment:"
	@$(call check_local_health,dev)
	@echo ""
	@echo "Stg environment:"
	@$(call check_local_health,stg)
	@echo ""
	@echo "Prod environment:"
	@$(call check_local_health,prod)

health-local-dev:
	$(call check_local_health,dev)

health-local-stg:
	$(call check_local_health,stg)

health-local-prod:
	$(call check_local_health,prod)

health-remote-stg:
	$(call check_remote_health,stg)

health-remote-prod:
	$(call check_remote_health,prod)

# ────────────────────────────────────────────────────────────────────────────
# Remote Access
# ────────────────────────────────────────────────────────────────────────────

ssh-stage:
	$(call ssh_env,stg)

ssh-prod:
	$(call ssh_env,prod)

# ────────────────────────────────────────────────────────────────────────────
# Database Access
# ────────────────────────────────────────────────────────────────────────────

psql-dev:
	$(call psql_env,dev)

psql-stage:
	$(call psql_env,stg)

psql-prod:
	$(call psql_env,prod)

# ────────────────────────────────────────────────────────────────────────────
# Database Migrations
# ────────────────────────────────────────────────────────────────────────────

run-migrations-dev:
	$(call run_migrations_env,dev)

run-migrations-stage:
	$(call run_migrations_env,stg)

run-migrations-prod:
	$(call run_migrations_env,prod)

# ────────────────────────────────────────────────────────────────────────────
# Utilities
# ────────────────────────────────────────────────────────────────────────────

clean-local:
	@echo "🧹 Cleaning up local containers and volumes..."
	$(foreach env,$(ENVIRONMENTS),$(call clean_local_env,$(env)))
	@echo "Cleaning up unused volumes..."
	@docker volume prune -f 2>/dev/null || true
	@echo "✓ Local cleanup complete"

clean-local-dev:
	@echo "🧹 Cleaning up dev containers and volumes..."
	$(call clean_local_env,dev)
	@echo "Cleaning up unused volumes..."
	@docker volume prune -f 2>/dev/null || true
	@echo "✓ Dev cleanup complete"

clean-local-stg:
	@echo "🧹 Cleaning up stg containers and volumes..."
	$(call clean_local_env,stg)
	@echo "Cleaning up unused volumes..."
	@docker volume prune -f 2>/dev/null || true
	@echo "✓ Stg cleanup complete"

clean-local-prod:
	@echo "🧹 Cleaning up prod containers and volumes..."
	$(call clean_local_env,prod)
	@echo "Cleaning up unused volumes..."
	@docker volume prune -f 2>/dev/null || true
	@echo "✓ Prod cleanup complete"

clean-remote-stg:
	$(call clean_remote_env,stg)

clean-remote-prod:
	$(call clean_remote_env,prod)

clean: clean-local
	@echo "🧹 Cleanup complete (local only - use clean-remote-stg or clean-remote-prod for remote)"

logs:
	@echo "📋 Showing logs for all projects..."
	$(foreach env,$(ENVIRONMENTS),$(call show_logs_env,$(env)))
	@echo ""

logs-dev:
	$(call tail_logs_env,dev)

logs-stg:
	$(call tail_logs_env,stg)

logs-prod:
	$(call tail_logs_env,prod)

logs-miner-dev:
	$(call tail_logs_service_env,dev,miner)

logs-miner-stg:
	$(call tail_logs_service_env,stg,miner)

logs-miner-prod:
	$(call tail_logs_service_env,prod,miner)

logs-classifier-dev:
	$(call tail_logs_service_env,dev,classifier)

logs-classifier-stg:
	$(call tail_logs_service_env,stg,classifier)

logs-classifier-prod:
	$(call tail_logs_service_env,prod,classifier)

docker-exec-miner-dev-local:
	$(call docker_exec_env,dev,miner)

docker-exec-miner-stg-local:
	$(call docker_exec_env,stg,miner)

docker-exec-miner-prod-local:
	$(call docker_exec_env,prod,miner)

docker-exec-classifier-dev-local:
	$(call docker_exec_env,dev,classifier)

docker-exec-classifier-stg-local:
	$(call docker_exec_env,stg,classifier)

docker-exec-classifier-prod-local:
	$(call docker_exec_env,prod,classifier)

ps-local:
	@echo "📊 Local container status:"
	$(foreach env,$(ENVIRONMENTS),$(call show_container_status_env,$(env)))
	@echo ""

ps-remote:
	@echo "📊 Remote container status:"
	$(call show_remote_status_env,stg)
	@echo ""
	$(call show_remote_status_env,prod)

ps: ps-local ps-remote
	@echo "📊 Container status complete"

restart-dev:
	$(call restart_env,dev)

restart-stg:
	$(call restart_env,stg)

restart-prod:
	$(call restart_env,prod)

stop-dev:
	$(call stop_env,dev)

stop-stg:
	$(call stop_env,stg)

stop-prod:
	$(call stop_env,prod)


# ────────────────────────────────────────────────────────────────────────────
# Help
# ────────────────────────────────────────────────────────────────────────────

help:
	@echo "════════════════════════════════════════════════════════════════════"
	@echo "WhatsApp Miner - Available Commands"
	@echo "════════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Local Development:"
	$(call help_env_section,dev)
	@echo ""
	@echo "Staging Environment:"
	$(call help_env_section,stg)
	@echo ""
	@echo "Production Environment:"
	$(call help_env_section,prod)
	@echo ""
	@echo "Remote Deployment Testing:"
	@echo "  make stg-deploy             - Test staging deployment with act"
	@echo "  make prod-deploy            - Test prod deployment with act"
	@echo ""
	@echo "Secrets:"
	@echo "  make sync-secrets-docker    - Update .env.* from Doppler in docker format"
	@echo "  make sync-secrets-env       - Update .env.* from Doppler in env format"
	@echo ""
	@echo "Health Checks:"
	@echo "  make health-local           - Check all local container health"
	@echo ""
	@echo "Remote Access:"
	@echo "  make ssh-stage              - SSH into stage EC2 instance"
	@echo "  make ssh-prod               - SSH into prod EC2 instance"
	@echo ""
	@echo "Secrets:"
	@echo "  make sync-secrets-docker    - Update .env files from Doppler (docker format)"
	@echo "  make sync-secrets-env       - Update .env files from Doppler (env format)"
	@echo "  make generate-env-example   - Generate .env.example template"
	@echo ""
	@echo "Logs:"
	@echo "  make logs                   - Show logs for all projects"
	@echo ""
	@echo "Utilities:"
	@echo "  make ps                     - Show container status for all projects (local + remote)"
	@echo "  make ps-local               - Show local container status for all projects"
	@echo "  make ps-remote              - Show remote container status on EC2"
	@echo "  make clean                  - Clean local containers and volumes"
	@echo "  make clean-local            - Clean local containers and volumes"
	@echo "  make cache-clear            - Clear all caches"
	@echo "  make cache-clear-manual-classifier - Clear manual classifier cache"
	@echo "  make help                   - Show this help message"
	@echo ""
	@echo "Database Management:"
	@echo "  make reset-llm-processed-dev     - Reset llm_processed flag for all messages (dev)"
	@echo "  make reset-llm-processed-stg      - Reset llm_processed flag for all messages (stg)"
	@echo "  make reset-llm-processed-prod    - Reset llm_processed flag for all messages (prod)"
	@echo "  make reset-llm-processed-*-dry-run - Check how many messages would be reset (dry run)"
	@echo "  make llm-processed-stats-*       - Get statistics about processed messages"
	@echo ""
	@echo "PyCharm Remote Development (dev only):"
	@echo "  Use: make dev-local PORTS=911,912 DETACHED=true|false"
	@echo "  Default SSH ports:"
	@echo "    dev:  miner=911, classifier=912"
	@echo "  PyCharm connection: root@localhost:PORT (password: root)"
	@echo "  Example: make dev-local PORTS=922,923 DETACHED=false"
	@echo "  Note: SSH access only available in development environment"
	@echo ""
	@echo "════════════════════════════════════════════════════════════════════"


# ────────────────────────────────────────────────────────────────────────────
# Dump Production Database (timestamped snapshot)
# ────────────────────────────────────────────────────────────────────────────
dump-prod-db:
	@echo "🧩 Dumping production database via Doppler..."
	@mkdir -p data_snapshots
	@TIMESTAMP=$$(date +%Y_%m_%d__%H_%M_%S); \
		DUMP_FILE="data_snapshots/prod_dump_$${TIMESTAMP}.backup"; \
		DUMP_FILE="$${DUMP_FILE}" doppler run --project whatsapp_miner_backend --config prd -- \
		bash -c 'pg_dump "$$SUPABASE_DATABASE_CONNECTION_STRING_SESSION_POOLER" \
		-F c -b -v -f "$${DUMP_FILE}" && echo "File created: $$(ls -la "$${DUMP_FILE}")"'; \
		ln -sf "$${DUMP_FILE}" data_snapshots/latest_prod_dump.backup; \
		echo "✅ Dump complete: $${DUMP_FILE} (linked to latest_prod_dump.backup)"

# ────────────────────────────────────────────────────────────────────────────
# Rebuild local dev DB from latest production snapshot
# ────────────────────────────────────────────────────────────────────────────
rebuild-dev-db-from-prod:
	@echo "🛑 Stopping dev stack and removing volumes (clean DB reset)..."
	@$(call docker_compose_local,dev,down -v --remove-orphans) 2>/dev/null || true
	@echo "🚀 Recreating dev environment (this will restore DB on fresh init if snapshot exists)..."
	@$(MAKE) dev-local

# ────────────────────────────────────────────────────────────────────────────
# Cache Management
# ────────────────────────────────────────────────────────────────────────────

cache-clear-manual-classifier:
	@echo "🗑️  Clearing manual classifier cache..."
	@rm -rf cache/manual_classifier
	@echo "✓ Manual classifier cache cleared"

cache-clear:
	@echo "🗑️  Clearing all caches..."
	@echo "Clearing manual classifier cache..."
	@rm -rf cache/
	@echo "✓ All caches cleared"

# ────────────────────────────────────────────────────────────────────────────
# Database Management
# ────────────────────────────────────────────────────────────────────────────

# Function to run database management commands
# Parameters: $(1)=env, $(2)=action, $(3)=dry_run_flag
define run_db_management
@echo "$(if $(3),🔍 DRY RUN: Checking how many messages would be affected in $(1) environment...,🔄 $(2) for $(1) environment...)"
@doppler run --project $(DOPPLER_PROJECT) --config $(call extract_doppler_config,$(1)) --command 'cd $$WORKING_DIR && /mnt/c/Users/noams/src/whatsapp_miner/.venv/bin/python -m src.db.utils.manual_db_changes $(2)$(if $(3), --dry-run)'
endef

# Named entry points for reset operations
reset-llm-processed-dev:
	$(call run_db_management,dev,reset)

reset-llm-processed-stg:
	$(call run_db_management,stg,reset)

reset-llm-processed-prod:
	$(call run_db_management,prod,reset)

# Named entry points for dry run operations
reset-llm-processed-dev-dry-run:
	$(call run_db_management,dev,reset,true)

reset-llm-processed-stg-dry-run:
	$(call run_db_management,stg,reset,true)

reset-llm-processed-prod-dry-run:
	$(call run_db_management,prod,reset,true)

# Named entry points for statistics
llm-processed-stats-dev:
	$(call run_db_management,dev,stats)

llm-processed-stats-stg:
	$(call run_db_management,stg,stats)

llm-processed-stats-prod:
	$(call run_db_management,prod,stats)

