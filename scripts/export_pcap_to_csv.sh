#!/usr/bin/env bash
# Usage: export_pcap_to_csv.sh <scenario>
# Converts logs/pcap/capture_<scenario>.pcap → logs/csv/capture_<scenario>.csv

SCENARIO="${1:-A}"
PCAP="/app/logs/pcap/capture_${SCENARIO}.pcap"
CSV="/app/logs/csv/capture_${SCENARIO}.csv"

if [ ! -f "$PCAP" ]; then
  echo "File not found: $PCAP"; exit 1
fi

# TODO: replace with tshark or scapy-based parser for richer field extraction
tcpdump -r "$PCAP" -tttt -n | awk '{print NR","$1","$2","$3,$4,$5}' > "$CSV"
echo "[export] $PCAP → $CSV"
