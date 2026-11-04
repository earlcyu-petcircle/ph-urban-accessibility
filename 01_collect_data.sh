#!/usr/bin/env bash
# Phase 1: download every open source into data/raw/ (gitignored).
#   ./01_collect_data.sh             keep files already in data/raw/
#   ./01_collect_data.sh --refresh   download everything again (new OpenStreetMap and Overture snapshots)
# The PSA 2024 census workbooks and the DOH facility registry cannot be fetched by script:
# download them by hand into data/manual/ before 02_build_tables.sh.
# Stub until PR 2.
source "$(dirname "$0")/src/shared/setup.sh"

ARGS=()
for arg in "$@"; do
  case "$arg" in
    --refresh) ARGS+=(--refresh) ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done

bash src/01_collect_data/download_sources.sh "${ARGS[@]+"${ARGS[@]}"}"
run_python src/01_collect_data/download_overture.py "${ARGS[@]+"${ARGS[@]}"}"
