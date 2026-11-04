#!/usr/bin/env bash
# Run every pipeline stage in order: collect, build, analyse, publish.
# A thin wrapper only: all logic lives in the mma package (src/mma/).
set -euo pipefail
cd "$(dirname "$0")"
exec uv run mma all "$@"
