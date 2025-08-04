#!/usr/bin/env bash
set -euo pipefail

# Database Migration Wrapper Script
# This script provides a convenient wrapper around the Python migration script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Function to show usage
show_usage() {
    cat << EOF
Database Migration Script

Usage:
    ./migrate_db.sh --src <source_config> --dst <destination_config> [options]

Arguments:
    --src    Source doppler config (e.g., 'dev', 'dev_personal')
    --dst    Destination doppler config (e.g., 'prd')

Options:
    --no-backup    Skip backing up destination database before migration (use with caution)
    --clear        Drop all tables in destination database before migration (use with caution)
    --verbose      Enable verbose logging
    --help         Show this help message

Examples:
    ./migrate_db.sh --src dev --dst prd
    ./migrate_db.sh --src dev_personal --dst prd
    ./migrate_db.sh --src dev --dst prd --no-backup --verbose
    ./migrate_db.sh --src dev --dst prd --clear
    ./migrate_db.sh --src dev --dst prd --clear --no-backup

EOF
}

# Parse arguments
ARGS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_usage
            exit 0
            ;;
        --src)
            SRC_CONFIG="$2"
            shift 2
            ;;
        --dst)
            DST_CONFIG="$2"
            shift 2
            ;;
        --no-backup)
            NO_BACKUP="--no-backup"
            shift
            ;;
        --clear)
            CLEAR="--clear"
            shift
            ;;
        --verbose)
            VERBOSE="--verbose"
            shift
            ;;
        *)
            ARGS+=("$1")
            shift
            ;;
    esac
done

# Validate required arguments
if [[ -z "${SRC_CONFIG:-}" ]]; then
    echo "Error: --src argument is required" >&2
    show_usage
    exit 1
fi

if [[ -z "${DST_CONFIG:-}" ]]; then
    echo "Error: --dst argument is required" >&2
    show_usage
    exit 1
fi

# Build command
CMD=("python3" "$SCRIPT_DIR/db_migrate.py" "--src" "$SRC_CONFIG" "--dst" "$DST_CONFIG")

# Add optional arguments
if [[ -n "${NO_BACKUP:-}" ]]; then
    CMD+=("$NO_BACKUP")
fi

if [[ -n "${CLEAR:-}" ]]; then
    CMD+=("$CLEAR")
fi

if [[ -n "${VERBOSE:-}" ]]; then
    CMD+=("$VERBOSE")
fi

# Add any additional arguments
CMD+=("${ARGS[@]}")

echo "Running: ${CMD[*]}"
echo "Working directory: $PROJECT_ROOT"

# Change to project root and run the migration
cd "$PROJECT_ROOT"
exec "${CMD[@]}" 