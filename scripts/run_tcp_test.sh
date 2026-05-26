#!/usr/bin/env bash
# Usage: run_tcp_test.sh <scenario>
# Runs TCP file transfer for the given scenario and logs results.

SCENARIO="${1:-A}"
echo "[test] TCP | scenario $SCENARIO"

# TODO: invoke client.py in TCP mode with the target file
# docker exec ft-client python3 src/client.py --mode tcp --scenario "$SCENARIO"
