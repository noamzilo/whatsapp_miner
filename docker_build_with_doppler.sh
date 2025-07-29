#!/usr/bin/env bash
# docker_build_with_doppler.sh
# Local wrapper: inject secrets with Doppler, then call the core builder.
set -euo pipefail

doppler run --command "./docker_build.sh"
