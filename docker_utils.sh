#!/usr/bin/env bash
# docker_utils.sh
# Utility functions for Docker deployment scripts

# Unquote ALL environment variables by removing surrounding quotes
# Usage: unquote_doppler_vars
unquote_doppler_vars() {
    # Get all environment variables and unquote them
    while IFS='=' read -r var_name var_value; do
        # Skip empty lines, lines without '=', and invalid variable names
        if [[ -n "$var_name" && "$var_name" != *"="* && "$var_name" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
            # Remove surrounding quotes if present
            var_value="${var_value%\"}"
            var_value="${var_value#\"}"
            export "$var_name"="$var_value"
        fi
    done < <(env)
} 