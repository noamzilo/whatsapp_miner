#!/usr/bin/env bash
# setup_act.sh
# Pre-download Act runner image to avoid hanging on first run
set -euo pipefail

echo "📦 Setting up Act (GitHub Actions locally)..."

# Check if Act is installed
if ! command -v act &> /dev/null; then
    echo "❌ Act is not installed"
    echo "   Install with: curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash"
    exit 1
fi

echo "✅ Act is installed: $(act --version)"

# Check if runner image exists
if docker images | grep -q "catthehacker/ubuntu"; then
    echo "✅ GitHub Actions runner image already exists"
    echo "   Act deployments should start quickly"
else
    echo "📥 Downloading GitHub Actions runner image..."
    echo "   This may take 2-5 minutes on first run"
    echo "   Image size: ~1.5GB"
    echo ""
    
    # Pull the runner image
    docker pull catthehacker/ubuntu:full-latest
    
    if [[ $? -eq 0 ]]; then
        echo "✅ Runner image downloaded successfully"
        echo "   Act deployments will now start quickly"
    else
        echo "❌ Failed to download runner image"
        exit 1
    fi
fi

echo ""
echo "🎉 Act setup complete!"
echo "   You can now run: .github/deploy_with_act.sh" 