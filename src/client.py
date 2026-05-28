import argparse
import os
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import rudp
from logger import TransferLogger
from tcp_transfer import send_file as _tcp_send

SERVER_HOST  = os.environ.get("SERVER_HOST", "172.20.0.10")
TCP_PORT     = int(os.environ.get("SERVER_TCP_PORT", 5000))
UDP_PORT     = int(os.environ.get("SERVER_UDP_PORT", 5001))
DEFAULT_FILE = os.environ.get("TRANSFER_FILE", "/app/data/input/test_1MB.bin")
WINDOW_SIZE  = int(os.environ.get("WINDOW_SIZE", "8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="File transfer client")
    parser.add_argument("--mode",     required=True, choices=["tcp", "rudp"])
    parser.add_argument("--scenario", required=True, choices=["A", "B", "C"])
    parser.add_argument("--file",     default=DEFAULT_FILE)
    args = parser.parse_args()

    mode      = args.mode.upper()
    path      = args.file
    file_size = Path(path).stat().st_size

    print(
        f"[client] {path} ({file_size} bytes) → {SERVER_HOST}"
        f"  mode={mode} scenario={args.scenario}",
        flush=True,
    )

    logger = TransferLogger(
        role="client", mode=mode, scenario=args.scenario, file_size=file_size
    )

    if mode == "TCP":
        with socket.create_connection((SERVER_HOST, TCP_PORT), timeout=120) as conn:
            _tcp_send(conn, path, logger)
    else:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            rudp.send_file(sock, (SERVER_HOST, UDP_PORT), path, logger, window_size=WINDOW_SIZE)

    print(f"[client] done — transfer_id={logger.transfer_id}", flush=True)


if __name__ == "__main__":
    main()
