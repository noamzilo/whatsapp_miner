#!/bin/bash
"""
Test Runner Script

This script runs the pytest tests for the WhatsApp Miner project.
"""

set -e

echo "🧪 Running WhatsApp Miner Tests"
echo "================================"

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Warning: Not in a virtual environment"
    echo "💡 Consider activating your virtual environment first"
fi

# Install dev dependencies if needed
echo "📦 Installing/updating dev dependencies..."
poetry install --with dev

# Run the tests
echo "🚀 Running tests..."
doppler run -- poetry run pytest tests/ -v --tb=short

echo "✅ Tests completed!" 