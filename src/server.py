import os
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tcp_transfer import receive_file

HOST = os.environ.get("SERVER_HOST", "0.0.0.0")
TCP_PORT = int(os.environ.get("SERVER_TCP_PORT", 5000))
RECV_DIR = os.environ.get("RECV_DIR", "/app/data/received")


def main() -> None:
    Path(RECV_DIR).mkdir(parents=True, exist_ok=True)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, TCP_PORT))
        srv.listen()
        print(f"[server] listening on {HOST}:{TCP_PORT}", flush=True)

        while True:
            conn, addr = srv.accept()
            print(f"[server] connection from {addr}", flush=True)
            with conn:
                try:
                    result = receive_file(conn, RECV_DIR)
                    hdr = result["header"]
                    print(
                        f"[server] {result['status']} — transfer {hdr['transfer_id']}"
                        f"  mode={hdr['mode']} scenario={hdr['scenario']}"
                        f"  {result['bytes_received']} bytes → {result['path']}",
                        flush=True,
                    )
                except Exception as exc:
                    print(f"[server] error: {exc}", flush=True)


if __name__ == "__main__":
    main()
