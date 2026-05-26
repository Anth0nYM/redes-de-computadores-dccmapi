#!/usr/bin/env bash
# Low-level helper: starts tcpdump and prints its PID.
# Do NOT call this directly in tests — use run_experiment.sh, which handles
# the readiness signal (waiting for "listening on") and graceful shutdown.
#
# Usage: capture_tcpdump.sh <scenario> <mode> [interface]

SCENARIO="${1:?scenario required}"
MODE="${2:?mode required}"
IFACE="${3:-eth0}"
PCAP="/app/logs/pcap/capture_${MODE}_${SCENARIO}.pcap"
READY_LOG="/tmp/tcpdump_${MODE}_${SCENARIO}.log"
PID_FILE="/tmp/tcpdump_${MODE}_${SCENARIO}.pid"

tcpdump -i "$IFACE" -w "$PCAP" 2>"$READY_LOG" &
echo $! > "$PID_FILE"
echo "[tcpdump] pid=$(cat $PID_FILE) — writing to $PCAP"
