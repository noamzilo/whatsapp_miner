#!/bin/bash
"""
Test Runner Script

This script runs the pytest tests for the WhatsApp Miner project.
"""

set -e

echo "🧪 Running WhatsApp Miner Tests"
echo "================================"

# Sync the env to the lockfile (creates .venv on first run)
echo "📦 Syncing dependencies..."
uv sync --frozen

# Run the tests
echo "🚀 Running tests..."
doppler run -- uv run --frozen pytest tests/ -v --tb=short

echo "✅ Tests completed!" 