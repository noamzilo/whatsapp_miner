#!/usr/bin/env bash
set -euo pipefail

# ── Load secrets from Doppler
eval "$(doppler secrets download --no-file --format env)"

: "${AWS_EC2_HOST_ADDRESS:?}"
: "${AWS_EC2_USERNAME:?}"
: "${AWS_EC2_PEM_CHATBOT_SA_B64:?}"
: "${AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER:?}"

# ── Create temp SSH key
KEY_FILE=$(mktemp)
echo "$AWS_EC2_PEM_CHATBOT_SA_B64" | base64 -d > "$KEY_FILE"
chmod 400 "$KEY_FILE"

# ── Create remote script
LOCAL_SCRIPT=$(mktemp)
cat <<'EOF' > "$LOCAL_SCRIPT"
#!/usr/bin/env bash
set -euo pipefail
echo "✅ Hello from EC2 at $(hostname)"
EOF

# ── Upload and run
scp -i "$KEY_FILE" -o StrictHostKeyChecking=no "$LOCAL_SCRIPT" "$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS:/tmp/remote_test.sh"
ssh -i "$KEY_FILE" -o StrictHostKeyChecking=no "$AWS_EC2_USERNAME@$AWS_EC2_HOST_ADDRESS" "chmod +x /tmp/remote_test.sh && /tmp/remote_test.sh"

# ── Clean up
rm "$KEY_FILE" "$LOCAL_SCRIPT"
