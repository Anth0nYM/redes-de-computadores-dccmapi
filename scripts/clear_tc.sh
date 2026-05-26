#!/usr/bin/env bash
IFACE="${1:-eth0}"
tc qdisc del dev "$IFACE" root 2>/dev/null && echo "[tc] rules cleared on $IFACE" || echo "[tc] no rules to clear on $IFACE"
