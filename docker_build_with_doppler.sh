#!/usr/bin/env bash
# Local wrapper: inject secrets with Doppler, then call the core builder.
set -euo pipefail

doppler run --command "./docker_build.sh"
