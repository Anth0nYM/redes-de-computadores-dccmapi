#!/usr/bin/env bash
# Usage: capture_tcpdump.sh <scenario> [interface]
# Captures traffic to logs/pcap/capture_<scenario>.pcap

SCENARIO="${1:-A}"
IFACE="${2:-eth0}"
OUTFILE="/app/logs/pcap/capture_${SCENARIO}.pcap"

echo "[tcpdump] capturing on $IFACE → $OUTFILE"
tcpdump -i "$IFACE" -w "$OUTFILE" &
TCPDUMP_PID=$!
echo "[tcpdump] pid=$TCPDUMP_PID"
echo $TCPDUMP_PID > /tmp/tcpdump.pid
