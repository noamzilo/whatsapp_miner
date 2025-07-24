#!/usr/bin/env bash
# Inject Doppler secrets and run the deploy workflow with `act`.
set -euo pipefail

doppler secrets download --no-file --format env \
	| sed 's/^/-s /' \
	| xargs act -W .github/workflows/deploy.yml
