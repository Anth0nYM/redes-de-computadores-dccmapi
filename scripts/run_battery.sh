#!/usr/bin/env bash
# Runs the full experiment battery: N repetitions × 2 modes × 3 scenarios.
#
# Usage (from repo root):
#   ./scripts/run_battery.sh [reps]
#   reps: number of repetitions (default: 30)
#
# Output:
#   logs/pcap/capture_<mode>_<scenario>_<rep>.pcap  — one pcap per run
#   logs/app/battery_<timestamp>.log                — full terminal transcript
#   logs/app/client_transfers.jsonl                 — appended by client
#   logs/app/server_transfers.jsonl                 — appended by server

set -uo pipefail

REPS="${1:-30}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$REPO_ROOT/logs/app/battery_${TIMESTAMP}.log"

mkdir -p "$REPO_ROOT/logs/app" "$REPO_ROOT/logs/pcap"

log()  { echo "[battery] $*" | tee -a "$LOG_FILE"; }
warn() { echo "[battery] WARNING: $*" | tee -a "$LOG_FILE"; }

TOTAL=$(( REPS * 6 ))
COUNT=0
FAILED=0

log "========================================================"
log "Battery start — $(date)"
log "Repetitions : $REPS"
log "Combinations: tcp/rudp × A/B/C = 6 per repetition"
log "Total runs  : $TOTAL"
log "Log file    : $LOG_FILE"
log "========================================================"

for rep in $(seq -w 1 "$REPS"); do
    log ""
    log "──────────────────────────────────────────────────────"
    log "Repetition ${rep} / ${REPS}"
    log "──────────────────────────────────────────────────────"

    for mode in tcp rudp; do
        for sc in A B C; do
            COUNT=$(( COUNT + 1 ))
            log "[${COUNT}/${TOTAL}] mode=${mode} scenario=${sc} rep=${rep}"

            if bash "$SCRIPT_DIR/run_experiment.sh" "$mode" "$sc" "$rep" \
                    2>&1 | tee -a "$LOG_FILE"; then
                log "  → OK"
            else
                FAILED=$(( FAILED + 1 ))
                warn "  → FAILED (mode=${mode} scenario=${sc} rep=${rep}) — continuing"
            fi
        done
    done
done

log ""
log "========================================================"
log "Battery done — $(date)"
log "Completed : $(( COUNT - FAILED )) / $TOTAL"
log "Failed    : $FAILED / $TOTAL"
log "Log file  : $LOG_FILE"
log "========================================================"
