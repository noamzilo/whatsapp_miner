#!/usr/bin/env bash
# docker_run_with_doppler.sh
# Local wrapper: inject secrets via Doppler, then pass through args.
set -euo pipefail

doppler run --command "./docker_run.sh $*"
