#!/usr/bin/env bash
# Usage: run_rudp_test.sh <scenario>
# Runs R-UDP file transfer for the given scenario and logs results.

SCENARIO="${1:-A}"
echo "[test] R-UDP | scenario $SCENARIO"

# TODO: invoke client.py in R-UDP mode with the target file
# docker exec ft-client python3 src/client.py --mode rudp --scenario "$SCENARIO"
