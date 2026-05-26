import os
import socket

SERVER_HOST = os.environ.get("SERVER_HOST", "172.20.0.10")
TCP_PORT = int(os.environ.get("SERVER_TCP_PORT", 5000))

# TODO: implement TCP and R-UDP file transfer client
if __name__ == "__main__":
    print(f"[client] connecting to {SERVER_HOST}:{TCP_PORT}")
    with socket.create_connection((SERVER_HOST, TCP_PORT), timeout=5) as s:
        msg = s.recv(64)
        print(f"[client] server says: {msg.decode().strip()}")
