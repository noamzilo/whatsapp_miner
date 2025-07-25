#!/usr/bin/env bash
set -euo pipefail

USER_ID=$(id -u)
GROUP_ID=$(getent group docker | cut -d: -f3)

doppler secrets download --no-file --format env \
	| sed 's/^/-s /' \
	| xargs act \
		--container-options "-u $USER_ID:$GROUP_ID" \
		-W .github/workflows/deploy.yml
