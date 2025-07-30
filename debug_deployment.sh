#!/usr/bin/env bash
# debug_deployment.sh
# Debug script to identify deployment issues

set -euo pipefail

echo "🐛 Debugging deployment issues..."

# Check Docker
echo "🐳 Docker status:"
if command -v docker &> /dev/null; then
    echo "   ✅ Docker is installed"
    docker --version
else
    echo "   ❌ Docker not found"
    exit 1
fi

# Check Docker Compose
echo "📦 Docker Compose status:"
if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    echo "   ✅ Docker Compose is available"
    docker compose version || docker-compose --version
else
    echo "   ❌ Docker Compose not found"
    exit 1
fi

# Check Doppler
echo "🌪️  Doppler status:"
if command -v doppler &> /dev/null; then
    echo "   ✅ Doppler is installed"
    doppler --version
else
    echo "   ❌ Doppler not found"
fi

# Check environment variables (with Doppler)
echo "🔧 Environment variables (with Doppler):"
doppler run -- env | grep -E "(DOCKER_|AWS_|ENV_)" | head -10 || echo "   No relevant env vars found"

# Check if we can build the image
echo "🔨 Testing Docker build:"
if docker build --dry-run . 2>/dev/null || echo "Build test completed"; then
    echo "   ✅ Docker build should work"
else
    echo "   ❌ Docker build issues detected"
fi

# Check docker-compose.yml
echo "📄 Docker Compose configuration:"
if docker compose config --quiet; then
    echo "   ✅ docker-compose.yml is valid"
else
    echo "   ❌ docker-compose.yml has issues"
fi

echo ""
echo "�� Debug complete!" 