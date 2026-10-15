#!/bin/sh
# Seam 3 on Linux: run tests/test_mcp_cli.py in throwaway Docker containers (Python 3.9, no curl).
# Run 1: no /etc/machine-id (bare container). Run 2: with /etc/machine-id.
# Usage: dev/linux_mcp_tests.sh [asset-cache-dir]
set -eu
repo=$(cd "$(dirname "$0")/.." && pwd)
assets=${1:-"$HOME/.cache/coinwallet-test-assets"}
mkdir -p "$assets"
image=python:3.9-slim
for mode in no-machine-id machine-id; do
  echo "== Linux, $mode =="
  if [ "$mode" = machine-id ]; then prep='echo 0123456789abcdef0123456789abcdef > /etc/machine-id'; else prep='rm -f /etc/machine-id'; fi
  docker run --rm -e COINWALLET_TEST_CONTAINER=1 -e COINWALLET_TEST_ASSETS=/assets \
    -v "$repo:/repo:ro" -v "$assets:/assets" "$image" \
    sh -c "$prep && python3 /repo/tests/test_mcp_cli.py"
done
