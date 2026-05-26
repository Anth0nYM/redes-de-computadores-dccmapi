import os
import socket

HOST = os.environ.get("SERVER_HOST", "0.0.0.0")
TCP_PORT = int(os.environ.get("SERVER_TCP_PORT", 5000))
UDP_PORT = int(os.environ.get("SERVER_UDP_PORT", 5001))

print(f"[server] listening on TCP:{TCP_PORT} and UDP:{UDP_PORT}")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, TCP_PORT))
    s.listen()
    print("[server] ready — waiting for connections")
    while True:
        conn, addr = s.accept()
        with conn:
            print(f"[server] connection from {addr}")
            conn.sendall(b"HELLO\n")
