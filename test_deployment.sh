#!/usr/bin/env bash
# test_deployment.sh
# Test script to verify deployment flow works correctly

set -euo pipefail

echo "🧪 Testing deployment flow..."

# Test 1: Check if all required scripts exist
echo "📋 Checking required scripts..."
required_scripts=(
    "docker_deploy_with_doppler.sh"
    "docker_deploy.sh"
    "docker_run.sh"
    "docker_run_with_doppler.sh"
    "docker_remote_run.sh"
    "docker_run_core.sh"
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
EOF

if docker compose --env-file "$TEMP_ENV" config --quiet; then
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

echo ""
echo "🎉 All deployment flow checks passed!"
echo ""
echo "📚 Usage:"
echo "   Local deployment: ./docker_deploy_with_doppler.sh"
echo "   Local run only:   ./docker_run.sh"
echo "   Remote deployment: ./docker_run.sh --remote"
echo "" 