#!/usr/bin/env bash
# docker_utils.sh
# Utility functions for Docker deployment scripts

# Unquote Doppler variables by removing surrounding quotes
# Usage: unquote_doppler_vars
unquote_doppler_vars() {
    # List of variables that might have quotes
    local vars=(
        "DOCKER_IMAGE_NAME_WHATSAPP_MINER"
        "DOCKER_CONTAINER_NAME_WHATSAPP_MINER"
        "DOCKER_COMPOSE_SERVICES"
        "AWS_EC2_HOST_ADDRESS"
        "AWS_EC2_USERNAME"
        "AWS_EC2_PEM_CHATBOT_SA_B64"
        "AWS_EC2_WORKING_DIRECTORY_WHATSAPP_MINER"
        "AWS_IAM_WHATSAPP_MINER_ACCESS_KEY_ID"
        "AWS_IAM_WHATSAPP_MINER_ACCESS_KEY"
        "AWS_EC2_REGION"
        "GREEN_API_INSTANCE_API_TOKEN"
        "GREEN_API_INSTANCE_ID"
        "SUPABASE_DATABASE_CONNECTION_STRING"
        "SUPABASE_DATABASE_PASSWORD"
        "MESSAGE_CLASSIFIER_RUN_EVERY_SECONDS"
        "GROQ_API_KEY"
        "ENVIRONMENT"
        "ENV_NAME"
        "ENV_FILE"
    )
    
    for var in "${vars[@]}"; do
        if [[ -n "${!var:-}" ]]; then
            # Remove surrounding quotes if present
            local value="${!var}"
            value="${value%\"}"
            value="${value#\"}"
            export "$var"="$value"
        fi
    done
} 