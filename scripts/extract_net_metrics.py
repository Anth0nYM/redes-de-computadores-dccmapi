#!/usr/bin/env python3
"""Extrai o RTT medido de cada pcap da bateria (host-side, via tcpdump) e grava
logs/csv/pcap_rtt.csv. O RTT é estimado como o intervalo entre os DOIS PRIMEIROS
pacotes cliente→servidor do fluxo relevante: o 1º é o SYN/início; o 2º é a resposta
do cliente ao SYN-ACK do servidor, que só ocorre após UM round-trip completo. A
captura é feita no servidor, então esse intervalo ≈ RTT ≈ 2 × atraso do cenário.

Filtra por protocolo (UDP porta 5001 para R-UDP; TCP porta 5000 para TCP) para
ignorar pacotes residuais de execuções vizinhas.

Uso:  python3 scripts/extract_net_metrics.py
Saída: logs/csv/pcap_rtt.csv  (colunas: mode, scenario, rep, rtt_ms)
"""
import csv
import glob
import os
import re
import subprocess

CLIENT = "172.20.0.20"
PCAP_DIR = "logs/pcap"
OUT = "logs/csv/pcap_rtt.csv"
NAME_RE = re.compile(r"capture_(tcp|rudp)_([ABC])_(\d+)\.pcap$")


def first_two_c2s_delta_ms(pcap: str, proto: str) -> float | None:
    """Retorna o intervalo (ms) entre os 2 primeiros pacotes c2s do fluxo, ou None."""
    out = subprocess.run(
        ["tcpdump", "-r", pcap, "-n", "-tt"],
        capture_output=True, text=True,
    ).stdout.splitlines()
    c2s = []
    for line in out:
        parts = line.split()
        if len(parts) < 3:
            continue
        # filtra o fluxo do protocolo: UDP 5001 (commplex-link) ou TCP 5000 (commplex-main)
        is_udp = "UDP" in line and "commplex-link" in line
        is_tcp = "commplex-main" in line
        if proto == "rudp" and not is_udp:
            continue
        if proto == "tcp" and not is_tcp:
            continue
        try:
            ts = float(parts[0])
        except ValueError:
            continue
        src = parts[2]  # ex.: 172.20.0.20.38963
        if src.startswith(CLIENT):
            c2s.append(ts)
            if len(c2s) >= 2:
                return (c2s[1] - c2s[0]) * 1000.0
    return None


def main() -> None:
    rows = []
    for pcap in sorted(glob.glob(f"{PCAP_DIR}/capture_*.pcap")):
        m = NAME_RE.search(os.path.basename(pcap))
        if not m:
            continue
        proto, scenario, rep = m.group(1), m.group(2), int(m.group(3))
        rtt = first_two_c2s_delta_ms(pcap, proto)
        if rtt is None:
            print(f"  aviso: RTT não extraído de {os.path.basename(pcap)}")
            continue
        rows.append({"mode": proto.upper(), "scenario": scenario,
                     "rep": rep, "rtt_ms": round(rtt, 3)})

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["mode", "scenario", "rep", "rtt_ms"])
        w.writeheader()
        w.writerows(rows)
    print(f"OK — {len(rows)} pcaps processados -> {OUT}")


if __name__ == "__main__":
    main()
