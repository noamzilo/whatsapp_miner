#!/usr/bin/env bash
# docker_show_status.sh
# Shows container status for both local and remote deployments

set -euo pipefail

echo "🔍 Checking container status..."

# Check local containers
echo "📱 Local containers:"
if docker compose ps 2>/dev/null | grep -q "whatsapp_miner"; then
    echo "   ✅ Local containers are running"
    docker compose ps
else
    echo "   ❌ No local containers found"
fi

echo ""

# Check remote containers (if AWS variables are available)
if [[ -n "${AWS_EC2_HOST_ADDRESS:-}" && -n "${AWS_EC2_USERNAME:-}" && -n "${AWS_EC2_PEM_CHATBOT_SA_B64:-}" ]]; then
    echo "☁️  Remote containers:"
    
    # Prepare SSH key
    KEY_FILE="$(mktemp)"
    echo "$AWS_EC2_PEM_CHATBOT_SA_B64" | base64 -d > "$KEY_FILE"
    chmod 400 "$KEY_FILE"
    trap 'rm -f "$KEY_FILE"' EXIT INT TERM
    
    ssh_cmd() { ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS" "$@"; }
    
    if ssh_cmd "docker ps | grep whatsapp_miner" 2>/dev/null; then
        echo "   ✅ Remote containers are running"
        ssh_cmd "docker ps | grep whatsapp_miner" 2>/dev/null || true
    else
        echo "   ❌ No remote containers found"
    fi
else
    echo "☁️  Remote containers: AWS variables not available"
fi

echo ""
echo "📊 Summary:"
echo "   Local: $(docker compose ps -q 2>/dev/null | wc -l) container(s)"
if [[ -n "${AWS_EC2_HOST_ADDRESS:-}" ]]; then
    REMOTE_COUNT="$(ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS" "docker ps | grep whatsapp_miner | wc -l" 2>/dev/null || echo "0")"
    echo "   Remote: $REMOTE_COUNT container(s)"
else
    echo "   Remote: AWS variables not available"
fi 