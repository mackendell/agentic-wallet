#!/bin/sh
# Seam 3 on Linux: run tests/test_mcp_cli.py in throwaway Docker containers (Python 3.9, no curl).
# Per platform: one run without /etc/machine-id (bare container), one with it (MCP v1.0.9+ no longer uses it;
# the service makes its own key in <data>/.key/ unless COINSDO_MASTER_KEY_FILE or a Docker secret is set).
# Usage: dev/linux_mcp_tests.sh [asset-cache-dir]
#        PLATFORMS="linux/arm64 linux/amd64" dev/linux_mcp_tests.sh     (amd64 runs emulated on an arm64 Mac)
set -eu
repo=$(cd "$(dirname "$0")/.." && pwd)
assets=${1:-"$HOME/.cache/coinwallet-test-assets"}
mkdir -p "$assets"
image=python:3.9-slim
for platform in ${PLATFORMS:-native}; do
  opt=""
  [ "$platform" = native ] || opt="--platform $platform"
  for mode in no-machine-id machine-id; do
    echo "== Linux $platform, $mode =="
    if [ "$mode" = machine-id ]; then prep='echo 0123456789abcdef0123456789abcdef > /etc/machine-id'; else prep='rm -f /etc/machine-id'; fi
    # shellcheck disable=SC2086
    docker run --rm $opt -e COINWALLET_TEST_CONTAINER=1 -e COINWALLET_TEST_ASSETS=/assets \
      -v "$repo:/repo:ro" -v "$assets:/assets" "$image" \
      sh -c "$prep && python3 /repo/tests/test_mcp_cli.py"
  done
done
