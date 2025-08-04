#!/usr/bin/env bash
# docker_validate_setup.sh
# Validates that all deployment prerequisites are met

set -euo pipefail

echo "🧪 Validating deployment setup..."

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
TEMP_ENV_DEV="$(mktemp)"
TEMP_ENV_PRD="$(mktemp)"
trap 'rm -f "$TEMP_ENV" "$TEMP_ENV_DEV" "$TEMP_ENV_PRD"' EXIT
cat > "$TEMP_ENV" << EOF
DOCKER_IMAGE_NAME_WHATSAPP_MINER=dummy/image:latest
DOCKER_CONTAINER_NAME_WHATSAPP_MINER=dummy_container
ENV_FILE=$TEMP_ENV
ENV_FILE_DEV=$TEMP_ENV_DEV
ENV_FILE_PRD=$TEMP_ENV_PRD
EOF

cp "$TEMP_ENV" "$TEMP_ENV_DEV"
cp "$TEMP_ENV" "$TEMP_ENV_PRD"

if ENV_FILE="$TEMP_ENV" ENV_FILE_DEV="$TEMP_ENV_DEV" ENV_FILE_PRD="$TEMP_ENV_PRD" docker compose config --quiet; then
    echo "   ✅ docker-compose.yml is valid"
else
    echo "   ❌ docker-compose.yml has syntax errors"
    exit 1
fi

# Test 5: Check if Doppler is available (for local testing)
echo "🌪️  Checking Doppler availability..."
if command -v doppler &> /dev/null; then
    echo "   ✅ Doppler is installed"
else
    echo "   ⚠️  Doppler not found (required for local deployment)"
fi

# Test 6: Check if alembic is available
echo "🗄️  Checking migration tools..."
if command -v poetry &> /dev/null && poetry run alembic --version &> /dev/null; then
    echo "   ✅ Alembic is available"
else
    echo "   ❌ Alembic not found (required for migrations)"
    exit 1
fi

# Test 7: Check if Redis queue infrastructure exists
echo "🔌 Checking Redis queue infrastructure..."
if [[ -f "src/message_queue/redis_streams_queue.py" ]]; then
    echo "   ✅ Redis Streams queue module exists"
else
    echo "   ❌ Redis Streams queue module missing"
    exit 1
fi

if [[ -f "src/message_classification/classify_messages_from_queue.py" ]]; then
    echo "   ✅ Queue classifier module exists"
else
    echo "   ❌ Queue classifier module missing"
    exit 1
fi

# Test 8: Check if database connection works (if Doppler is available)
echo "🔌 Testing database connections..."
if command -v doppler &> /dev/null; then
    # Test dev database
    if doppler run --project whatsapp_miner_backend --config dev_personal -- poetry run alembic current &> /dev/null; then
        echo "   ✅ Dev database connection works"
    else
        echo "   ❌ Dev database connection failed"
        exit 1
    fi
    
    # Test production database
    if doppler run --project whatsapp_miner_backend --config prd -- poetry run alembic current &> /dev/null; then
        echo "   ✅ Production database connection works"
    else
        echo "   ❌ Production database connection failed"
        exit 1
    fi
else
    echo "   ⚠️  Skipping database connection tests (Doppler not available)"
fi

echo ""
echo "🎉 All deployment setup validation passed!"
echo ""
echo "📚 Usage:"
echo "   Local deployment: ./docker_deploy_with_doppler.sh"
echo "   Local run only:   ./docker_run.sh"
echo "   Remote deployment: ./docker_run.sh --remote"
echo "   Run migrations:   ./run_migrations.sh --env dev|prd"
echo "" 