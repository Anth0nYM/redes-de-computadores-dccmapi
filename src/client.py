import argparse
import os
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from logger import TransferLogger
from tcp_transfer import send_file

SERVER_HOST = os.environ.get("SERVER_HOST", "172.20.0.10")
TCP_PORT = int(os.environ.get("SERVER_TCP_PORT", 5000))
DEFAULT_FILE = os.environ.get("TRANSFER_FILE", "/app/data/input/test_1MB.bin")


def main() -> None:
    parser = argparse.ArgumentParser(description="File transfer client")
    parser.add_argument("--mode", required=True, choices=["tcp", "rudp"])
    parser.add_argument("--scenario", required=True, choices=["A", "B", "C"])
    parser.add_argument("--file", default=DEFAULT_FILE)
    args = parser.parse_args()

    mode = args.mode.upper()
    path = args.file

    file_size = Path(path).stat().st_size
    logger = TransferLogger(role="client", mode=mode, scenario=args.scenario, file_size=file_size)

    print(f"[client] {path} ({file_size} bytes) → {SERVER_HOST}:{TCP_PORT}"
          f"  mode={mode} scenario={args.scenario}", flush=True)

    with socket.create_connection((SERVER_HOST, TCP_PORT), timeout=120) as conn:
        send_file(conn, path, logger)

    print(f"[client] done — transfer_id={logger.transfer_id}", flush=True)


if __name__ == "__main__":
    main()
