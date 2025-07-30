#!/usr/bin/env bash
# docker_validate_and_show_status.sh
# Validates deployment setup and shows container status

set -euo pipefail

echo "📊 Deployment Status Report"
echo "=========================="

# Run validation
echo ""
echo "🔍 Validating deployment setup..."
./docker_validate_setup.sh

# Show container status
echo ""
echo "📱 Container Status:"
./docker_show_status.sh

echo ""
echo "✅ Status report complete!" 