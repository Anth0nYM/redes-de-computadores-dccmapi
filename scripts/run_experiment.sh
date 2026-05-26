#!/usr/bin/env bash
# Orchestrates a single experiment run: tc → tcpdump → transfer → teardown.
#
# Usage (from host, targeting the server container):
#   ./scripts/run_experiment.sh <mode> <scenario>
#   mode:     tcp | rudp
#   scenario: A | B | C
#
# Example:
#   ./scripts/run_experiment.sh tcp A

set -euo pipefail

MODE="${1:?Usage: run_experiment.sh <mode> <scenario>}"
SCENARIO="${2:?Usage: run_experiment.sh <mode> <scenario>}"

SERVER="ft-server"
CLIENT="ft-client"
IFACE="eth0"
PCAP_REMOTE="/app/logs/pcap/capture_${MODE}_${SCENARIO}.pcap"
TCPDUMP_LOG="/tmp/tcpdump_${MODE}_${SCENARIO}.log"
TCPDUMP_PID_FILE="/tmp/tcpdump_${MODE}_${SCENARIO}.pid"

log() { echo "[experiment] $*"; }

# ── 1. apply tc rules on the server ──────────────────────────────────────────
log "applying tc scenario $SCENARIO on $SERVER"
docker exec "$SERVER" bash /app/scripts/apply_tc.sh "$SCENARIO" "$IFACE"

# ── 2. start tcpdump and wait until it is genuinely capturing ────────────────
log "starting tcpdump on $SERVER"
docker exec -d "$SERVER" bash -c "
  tcpdump -i $IFACE -w $PCAP_REMOTE 2>$TCPDUMP_LOG &
  echo \$! > $TCPDUMP_PID_FILE
"

# poll for the 'listening on' message — real readiness signal, no fixed sleep
log "waiting for tcpdump to be ready..."
WAIT=0
until docker exec "$SERVER" grep -q "listening on" "$TCPDUMP_LOG" 2>/dev/null; do
  sleep 0.1
  WAIT=$((WAIT + 1))
  if [ "$WAIT" -ge 50 ]; then   # 5 s timeout
    echo "[experiment] ERROR: tcpdump did not become ready in time" >&2
    exit 1
  fi
done
log "tcpdump ready (${WAIT}x100ms)"

# ── 3. run the transfer ───────────────────────────────────────────────────────
log "starting transfer: mode=$MODE scenario=$SCENARIO"
docker exec "$CLIENT" python3 src/client.py --mode "$MODE" --scenario "$SCENARIO"
log "transfer complete"

# ── 4. stop tcpdump gracefully: SIGTERM flushes the pcap buffer ──────────────
log "stopping tcpdump"
docker exec "$SERVER" bash -c "
  kill -SIGTERM \$(cat $TCPDUMP_PID_FILE) 2>/dev/null || true
  # wait up to 3 s for the process to finish flushing
  for i in \$(seq 1 30); do
    kill -0 \$(cat $TCPDUMP_PID_FILE) 2>/dev/null || break
    sleep 0.1
  done
"
log "tcpdump stopped — pcap saved to $PCAP_REMOTE"

# ── 5. clear tc rules ─────────────────────────────────────────────────────────
log "clearing tc rules on $SERVER"
docker exec "$SERVER" bash /app/scripts/clear_tc.sh "$IFACE"

log "done: mode=$MODE scenario=$SCENARIO"
