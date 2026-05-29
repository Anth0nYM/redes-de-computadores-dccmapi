#!/usr/bin/env bash
# export_pcap_to_csv.sh — convert pcap files to per-packet CSVs + aggregate summary
#
# Usage:
#   ./scripts/export_pcap_to_csv.sh all                        # all 180 pcaps + summary
#   ./scripts/export_pcap_to_csv.sh <mode> <scenario> <rep>   # single pcap + summary

set -euo pipefail

CONTAINER="ft-server"
PCAP_DIR_CONT="/app/logs/pcap"
CSV_DIR="logs/csv"
CLIENT_IP="172.20.0.20"
SERVER_IP="172.20.0.10"

mkdir -p "$CSV_DIR"

# ── Per-packet parser (receives tcpdump -tttt -n output on stdin) ─────────────
# Handles both full UDP/TCP packets and IP fragments (ip-proto-17).
# split_addr: 172.20.0.10.5000 (5 octets) → ("172.20.0.10", "5000")
#             172.20.0.10      (4 octets) → ("172.20.0.10", "")
PARSER='
import re, sys, csv

CLIENT, SERVER = sys.argv[1], sys.argv[2]

pat = re.compile(
    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)"
    r"\s+IP\s+(\S+)\s+>\s+(\S+):"
    r"(?:.*?length\s+(\d+))?"
)

def split_addr(addr):
    parts = addr.split(".")
    if len(parts) == 5:
        return ".".join(parts[:4]), parts[4]
    return addr, ""

rows = []
for line in sys.stdin:
    m = pat.search(line)
    if not m:
        continue
    ts_str, src_full, dst_full, length = m.groups()
    length = int(length) if length else 0
    src_ip, src_port = split_addr(src_full)
    dst_ip, dst_port = split_addr(dst_full)
    direction = "c2s" if src_ip == CLIENT else "s2c" if src_ip == SERVER else "other"
    proto = "UDP" if ("UDP," in line or "ip-proto-17" in line) else "TCP"
    fragment = "yes" if "ip-proto-17" in line else "no"
    rows.append({
        "frame":     len(rows) + 1,
        "timestamp": ts_str,
        "src_ip":    src_ip,  "src_port": src_port,
        "dst_ip":    dst_ip,  "dst_port": dst_port,
        "direction": direction,
        "proto":     proto,
        "length":    length,
        "fragment":  fragment,
    })

if not rows:
    sys.exit(0)
w = csv.DictWriter(sys.stdout, fieldnames=list(rows[0].keys()), lineterminator="\n")
w.writeheader()
w.writerows(rows)
'

# ── Parse one pcap → per-packet CSV ──────────────────────────────────────────
parse_one() {
    local mode="$1" sc="$2" rep="$3"
    local pcap="${PCAP_DIR_CONT}/capture_${mode}_${sc}_${rep}.pcap"
    local csv_out="${CSV_DIR}/capture_${mode}_${sc}_${rep}.csv"

    if ! docker exec "$CONTAINER" test -f "$pcap" 2>/dev/null; then
        echo "[skip] capture_${mode}_${sc}_${rep}.pcap" >&2
        return 0
    fi

    # A corrupt/truncated pcap makes tcpdump exit non-zero; with `set -e` that would
    # abort the whole batch, so isolate the failure and skip just this file.
    if ! docker exec "$CONTAINER" tcpdump -r "$pcap" -tttt -n 2>/dev/null \
         | python3 -c "$PARSER" "$CLIENT_IP" "$SERVER_IP" > "$csv_out"; then
        echo "[warn] capture_${mode}_${sc}_${rep}.pcap unreadable/corrupt — skipping" >&2
        rm -f "$csv_out"
        return 0
    fi

    local n=$(( $(wc -l < "$csv_out") - 1 ))
    echo "[ok] capture_${mode}_${sc}_${rep}.csv ($n packets)"
}

# ── Build pcap_summary.csv from all per-packet CSVs ──────────────────────────
# Columns used for cross-validation against JSONL app metrics:
#   pcap_duration_s   ↔  transfer_time_s
#   pcap_c2s_bytes    ↔  bytes_sent (client)
#   pcap_s2c_bytes    ↔  bytes_received (client, i.e. ACKs+control)
build_summary() {
    python3 - << 'PYEOF'
import csv, glob
from datetime import datetime
from pathlib import Path

CSV_DIR = "logs/csv"

def parse_ts(s):
    return datetime.strptime(s.strip(), "%Y-%m-%d %H:%M:%S.%f").timestamp()

rows = []
for f in sorted(glob.glob(f"{CSV_DIR}/capture_*.csv")):
    parts = Path(f).stem.split("_")
    if len(parts) != 4:
        continue
    _, mode, scenario, rep = parts

    pkts = list(csv.DictReader(open(f)))
    if not pkts:
        continue

    t0 = parse_ts(pkts[0]["timestamp"])
    t1 = parse_ts(pkts[-1]["timestamp"])

    c2s   = [p for p in pkts if p["direction"] == "c2s" and p["fragment"] == "no"]
    s2c   = [p for p in pkts if p["direction"] == "s2c" and p["fragment"] == "no"]
    frags = [p for p in pkts if p["fragment"] == "yes"]

    rows.append({
        "mode":               mode,
        "scenario":           scenario,
        "rep":                rep,
        "pcap_duration_s":    round(t1 - t0, 6),
        "pcap_packets":       len(pkts),
        "pcap_c2s_pkts":      len(c2s),
        "pcap_s2c_pkts":      len(s2c),
        "pcap_fragment_pkts": len(frags),
        "pcap_c2s_bytes":     sum(int(p["length"]) for p in c2s),
        "pcap_s2c_bytes":     sum(int(p["length"]) for p in s2c),
    })

if not rows:
    print("[summary] no CSVs found", flush=True)
    raise SystemExit(1)

out = f"{CSV_DIR}/pcap_summary.csv"
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print(f"[summary] {out} ({len(rows)} rows)")
PYEOF
}

# ── Entry point ───────────────────────────────────────────────────────────────
case "${1:-}" in
all)
    for mode in tcp rudp; do
        for sc in A B C; do
            for rep in $(seq -w 1 30); do
                parse_one "$mode" "$sc" "$rep"
            done
        done
    done
    build_summary
    ;;
*)
    [[ $# -eq 3 ]] || { echo "Usage: $0 all | <mode> <scenario> <rep>"; exit 1; }
    parse_one "$1" "$2" "$3"
    build_summary
    ;;
esac
