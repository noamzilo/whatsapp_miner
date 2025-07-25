#!/usr/bin/env bash
set -euo pipefail

USER_ID=$(id -u)
doppler secrets download --no-file --format env \
	| sed 's/^/-s /' \
	| xargs act --container-options "-u $USER_ID" -W .github/workflows/deploy.yml
