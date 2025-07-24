#!/usr/bin/env bash
# Local wrapper: inject secrets via Doppler, then pass through args.
set -euo pipefail

doppler run --command "./docker_run.sh $*"
