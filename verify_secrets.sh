#!/usr/bin/env bash
# Verify base64 secrets decode correctly and contain all required environment variables
set -euo pipefail

###############################################################################
# ── argument parsing ─────────────────────────────────────────────────────────
###############################################################################
SECRETS_B64=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --secrets-b64)  SECRETS_B64="$2";      shift 2;;
    --*)            echo "❌ Unknown flag $1"; exit 1;;
    *)              echo "❌ Unexpected arg $1"; exit 1;;
  esac
done

if [[ -z "$SECRETS_B64" ]]; then
  echo "❌ --secrets-b64 is required"; exit 1
fi

###############################################################################
# ── secret bundle decoding and verification ──────────────────────────────────
###############################################################################
echo "🔍 Verifying secrets bundle..."

# Create temporary file for decoded JSON
tmp_json="$(mktemp)"
trap 'rm -f "$tmp_json"' EXIT

# Decode base64 to JSON
if ! printf '%s' "$SECRETS_B64" | base64 -d > "$tmp_json" 2>/dev/null; then
  echo "❌ Failed to decode base64 secrets"
  exit 1
fi

# Verify JSON is valid
if ! jq empty "$tmp_json" 2>/dev/null; then
  echo "❌ Invalid JSON in secrets bundle"
  exit 1
fi

# Define required environment variables
required_vars=(
  "ENV_NAME"
  "AWS_EC2_HOST_ADDRESS"
  "AWS_EC2_PEM_CHATBOT_SA_B64"
  "AWS_EC2_REGION"
  "AWS_EC2_USERNAME"
  "AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER"
  "AWS_IAM_WHATSAPP_MINER_ACCESS_KEY"
  "AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID"
  "DOCKER_CONTAINER_NAME_WHATSAPP_MINER"
  "DOCKER_IMAGE_NAME_WHATSAPP_MINER"
  "GREEN_API_INSTANCE_API_TOKEN"
  "GREEN_API_INSTANCE_ID"
  "SUPABASE_DATABASE_CONNECTION_STRING"
  "SUPABASE_DATABASE_PASSWORD"
  "MESSAGE_CLASSIFIER_RUN_EVERY_SECONDS"
  "GROQ_API_KEY"
)

echo "📋 Checking required environment variables..."

# Check each required variable
missing_vars=()
for var in "${required_vars[@]}"; do
  if ! jq -e ".$var" "$tmp_json" >/dev/null 2>&1; then
    missing_vars+=("$var")
  else
    value=$(jq -r ".$var" "$tmp_json")
    if [[ -z "$value" ]]; then
      echo "⚠️  Warning: $var is present but empty"
    else
      echo "✅ $var: [PRESENT]"
    fi
  fi
done

# Report missing variables
if [[ ${#missing_vars[@]} -gt 0 ]]; then
  echo "❌ Missing required environment variables:"
  printf '  - %s\n' "${missing_vars[@]}"
  exit 1
fi

# Verify AWS credentials format (basic validation)
aws_access_key=$(jq -r '.AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID' "$tmp_json")
aws_secret_key=$(jq -r '.AWS_IAM_WHATSAPP_MINER_ACCESS_KEY' "$tmp_json")

if [[ ! "$aws_access_key" =~ ^AKIA[A-Z0-9]{16}$ ]]; then
  echo "⚠️  Warning: AWS_ACCESS_KEY_ID format may be invalid (should start with AKIA and be 20 chars)"
fi

if [[ ${#aws_secret_key} -ne 40 ]]; then
  echo "⚠️  Warning: AWS_SECRET_ACCESS_KEY should be 40 characters long"
fi

# Verify numeric fields
message_classifier_seconds=$(jq -r '.MESSAGE_CLASSIFIER_RUN_EVERY_SECONDS' "$tmp_json")
if ! [[ "$message_classifier_seconds" =~ ^[0-9]+$ ]]; then
  echo "❌ MESSAGE_CLASSIFIER_RUN_EVERY_SECONDS must be a number"
  exit 1
fi

# Verify connection string format
supabase_conn=$(jq -r '.SUPABASE_DATABASE_CONNECTION_STRING' "$tmp_json")
if [[ ! "$supabase_conn" =~ ^postgresql:// ]]; then
  echo "⚠️  Warning: SUPABASE_DATABASE_CONNECTION_STRING should start with 'postgresql://'"
fi

echo "✅ All required environment variables are present and valid!"
echo "📊 Summary: ${#required_vars[@]} variables verified successfully"
echo "🟢 Secrets verification completed successfully!" 