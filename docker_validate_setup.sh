#!/usr/bin/env bash
# docker_validate_setup.sh
# Validates that all deployment prerequisites are met
# Usage: ./docker_validate_setup.sh [--env dev|prd]

set -euo pipefail

# Parse arguments
ENVIRONMENT="dev"  # Default to dev

while [[ $# -gt 0 ]]; do
    case $1 in
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--env dev|prd]"
            exit 1
            ;;
    esac
done

# Validate environment
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "prd" ]]; then
    echo "❌ Error: Invalid environment '$ENVIRONMENT'. Must be dev or prd"
    exit 1
fi

echo "🧪 Validating deployment setup for environment: $ENVIRONMENT..."

# Test 1: Check if all required scripts exist
echo "📋 Checking required scripts..."
required_scripts=(
    "docker_deploy_with_doppler.sh"
    "docker_deploy.sh"
    "docker_run.sh"
    "docker_run_with_doppler.sh"
    "docker_remote_run.sh"
    "docker_run_core.sh"
    "run_migrations.sh"
)

for script in "${required_scripts[@]}"; do
    if [[ -f "$script" ]]; then
        echo "   ✅ $script exists"
    else
        echo "   ❌ $script missing"
        exit 1
    fi
done

# Test 2: Check if scripts are executable
echo "🔧 Checking script permissions..."
for script in "${required_scripts[@]}"; do
    if [[ -x "$script" ]]; then
        echo "   ✅ $script is executable"
    else
        echo "   ❌ $script is not executable"
        exit 1
    fi
done

# Test 3: Check if docker-compose.yml exists
echo "📄 Checking docker-compose.yml..."
if [[ -f "docker-compose.yml" ]]; then
    echo "   ✅ docker-compose.yml exists"
else
    echo "   ❌ docker-compose.yml missing"
    exit 1
fi

# Test 4: Check docker-compose.yml syntax (with dummy env vars)
echo "🔍 Checking docker-compose.yml syntax..."
# Create temporary env file with dummy values for validation
TEMP_ENV="$(mktemp)"
trap 'rm -f "$TEMP_ENV"' EXIT
cat > "$TEMP_ENV" << EOF
DOCKER_IMAGE_NAME_WHATSAPP_MINER=dummy/image:latest
DOCKER_CONTAINER_NAME_WHATSAPP_MINER=dummy_container
ENV_FILE=$TEMP_ENV
ENV_NAME=$ENVIRONMENT
EOF

if ENV_FILE="$TEMP_ENV" ENV_NAME="$ENVIRONMENT" docker compose config --quiet; then
    echo "   ✅ docker-compose.yml is valid"
else
    echo "   ❌ docker-compose.yml has syntax errors"
    exit 1
fi

# Test 5: Check if Doppler is available (for local testing only)
echo "🌪️  Checking Doppler availability..."
if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
    echo "   ✅ Running in GitHub Actions - Doppler not required"
elif command -v doppler &> /dev/null; then
    echo "   ✅ Doppler is installed"
else
    echo "   ⚠️  Doppler not found (required for local deployment)"
fi

# Test 6: Check if alembic is available
echo "🗄️  Checking migration tools..."
if command -v alembic &> /dev/null; then
    echo "   ✅ Alembic is available"
elif command -v poetry &> /dev/null && poetry run alembic --version &> /dev/null; then
    echo "   ✅ Alembic is available via Poetry"
else
    echo "   ❌ Alembic not found (required for migrations)"
    exit 1
fi

# Test 7: Check if database classifier module exists
echo "🔌 Checking database classifier infrastructure..."
if [[ -f "src/message_classification/classify_new_messages.py" ]]; then
    echo "   ✅ Database classifier module exists"
else
    echo "   ❌ Database classifier module missing"
    exit 1
fi

# Test 8: Check if database connection works for the specified environment
echo "🔌 Testing database connection for environment: $ENVIRONMENT..."
if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
    echo "   ✅ Running in GitHub Actions - database connection will be tested during deployment"
elif command -v doppler &> /dev/null; then
    # Map environment to Doppler config
    case "$ENVIRONMENT" in
        "dev")
            DOPPLER_CONFIG="dev_personal"
            ;;
        "prd")
            DOPPLER_CONFIG="prd"
            ;;
    esac
    
    # Test database connection for the specified environment
    # Try direct alembic first, then poetry run alembic
    if command -v alembic &> /dev/null; then
        if doppler run --project whatsapp_miner_backend --config "$DOPPLER_CONFIG" -- alembic current &> /dev/null; then
            echo "   ✅ $ENVIRONMENT database connection works"
        else
            echo "   ❌ $ENVIRONMENT database connection failed"
            exit 1
        fi
    elif command -v poetry &> /dev/null && poetry run alembic --version &> /dev/null; then
        if doppler run --project whatsapp_miner_backend --config "$DOPPLER_CONFIG" -- poetry run alembic current &> /dev/null; then
            echo "   ✅ $ENVIRONMENT database connection works"
        else
            echo "   ❌ $ENVIRONMENT database connection failed"
            exit 1
        fi
    else
        echo "   ❌ Alembic not available for database connection test"
        exit 1
    fi
else
    echo "   ⚠️  Skipping database connection tests (Doppler not available)"
fi

echo ""
echo "🎉 All deployment setup validation passed for environment: $ENVIRONMENT!"
echo ""
echo "📚 Usage:"
echo "   Local deployment: ./docker_deploy_with_doppler.sh --env $ENVIRONMENT"
echo "   Local run only:   ./docker_run.sh --env $ENVIRONMENT"
echo "   Remote deployment: ./docker_run.sh --env $ENVIRONMENT --remote"
echo "   Run migrations:   ./run_migrations.sh --env $ENVIRONMENT"
echo "" 