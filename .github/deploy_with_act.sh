#!/usr/bin/env bash
set -euo pipefail

# Load from Doppler and run act
doppler secrets download --no-file --format json | jq -r 'to_entries[] | "-s \(.key)=\(.value)"' | xargs act -W .github/workflows/deploy.yml
