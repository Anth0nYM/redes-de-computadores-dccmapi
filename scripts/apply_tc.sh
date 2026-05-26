#!/usr/bin/env bash
# Usage: apply_tc.sh <scenario> [interface]
#   scenario: A | B | C
#   interface: default eth0
#
# Scenario A: 0% loss / 10ms delay
# Scenario B: 10% loss / 50ms delay
# Scenario C: 20% loss / 100ms delay

IFACE="${2:-eth0}"
SCENARIO="${1:-A}"

tc qdisc del dev "$IFACE" root 2>/dev/null

case "$SCENARIO" in
  A) tc qdisc add dev "$IFACE" root netem delay 10ms ;;
  B) tc qdisc add dev "$IFACE" root netem delay 50ms loss 10% ;;
  C) tc qdisc add dev "$IFACE" root netem delay 100ms loss 20% ;;
  *) echo "Unknown scenario: $SCENARIO. Use A, B or C."; exit 1 ;;
esac

echo "[tc] scenario $SCENARIO applied on $IFACE"
tc qdisc show dev "$IFACE"
