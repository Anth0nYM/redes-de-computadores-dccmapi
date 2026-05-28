import os
import socket
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import rudp
import tcp_transfer

HOST     = os.environ.get("SERVER_HOST", "0.0.0.0")
TCP_PORT = int(os.environ.get("SERVER_TCP_PORT", 5000))
UDP_PORT = int(os.environ.get("SERVER_UDP_PORT", 5001))
RECV_DIR = os.environ.get("RECV_DIR", "/app/data/received")


def _tcp_loop() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, TCP_PORT))
        srv.listen()
        print(f"[server] TCP  listening on {HOST}:{TCP_PORT}", flush=True)
        while True:
            conn, addr = srv.accept()
            print(f"[server] TCP  connection from {addr}", flush=True)
            with conn:
                try:
                    r   = tcp_transfer.receive_file(conn, RECV_DIR)
                    hdr = r["header"]
                    print(
                        f"[server] TCP  {r['status']} — {hdr['transfer_id']}"
                        f"  scenario={hdr['scenario']}  {r['bytes_received']} bytes",
                        flush=True,
                    )
                except Exception as exc:
                    print(f"[server] TCP  error: {exc}", flush=True)


def _udp_loop() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as srv:
        srv.bind((HOST, UDP_PORT))
        print(f"[server] RUDP listening on {HOST}:{UDP_PORT}", flush=True)
        while True:
            try:
                r   = rudp.receive_file(srv, RECV_DIR)
                hdr = r["header"]
                print(
                    f"[server] RUDP {r['status']} — {hdr['transfer_id']}"
                    f"  scenario={hdr['scenario']}  {r['bytes_received']} bytes",
                    flush=True,
                )
            except Exception as exc:
                print(f"[server] RUDP error: {exc}", flush=True)


def main() -> None:
    Path(RECV_DIR).mkdir(parents=True, exist_ok=True)
    threading.Thread(target=_udp_loop, daemon=True).start()
    _tcp_loop()


if __name__ == "__main__":
    main()
