import os
import socket
import struct
import uuid
from pathlib import Path

from checksum import file_checksum
from logger import TransferLogger

# Header layout (256 bytes, big-endian / network order):
#   4s  magic        b"RDFT"
#   Q   file_size    uint64
#   16s transfer_id  UUID as raw bytes
#   B   scenario     0=A  1=B  2=C
#   B   mode         0=TCP  1=RUDP
#   226s x_custom_auth  null-padded UTF-8
HEADER_FMT = "!4sQ16sBB226s"
HEADER_SIZE = struct.calcsize(HEADER_FMT)  # 256
MAGIC = b"RDFT"
CHUNK_SIZE = 4096

SCENARIO_ENC = {"A": 0, "B": 1, "C": 2}
SCENARIO_DEC = {v: k for k, v in SCENARIO_ENC.items()}
MODE_ENC = {"TCP": 0, "RUDP": 1}
MODE_DEC = {v: k for k, v in MODE_ENC.items()}

# Set X_CUSTOM_AUTH=<matrícula> <nome> in the container environment.
_AUTH = os.environ.get("X_CUSTOM_AUTH", "20261011410 ANTHONY IRLAN MARQUES LUZ").encode("utf-8")[:226].ljust(226, b"\x00")


def _pack_header(transfer_id: str, file_size: int, scenario: str, mode: str) -> bytes:
    return struct.pack(
        HEADER_FMT,
        MAGIC,
        file_size,
        uuid.UUID(transfer_id).bytes,
        SCENARIO_ENC[scenario],
        MODE_ENC[mode],
        _AUTH,
    )


def _unpack_header(raw: bytes) -> dict:
    magic, file_size, tid_bytes, scenario_b, mode_b, auth_bytes = struct.unpack(HEADER_FMT, raw)
    if magic != MAGIC:
        raise ValueError(f"invalid magic: {magic!r}")
    return {
        "transfer_id": str(uuid.UUID(bytes=tid_bytes)),
        "file_size": file_size,
        "scenario": SCENARIO_DEC[scenario_b],
        "mode": MODE_DEC[mode_b],
        "x_custom_auth": auth_bytes.rstrip(b"\x00").decode("utf-8", errors="replace"),
    }


def _recv_exact(conn: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("connection closed before receiving full data")
        buf += chunk
    return bytes(buf)


def send_file(conn: socket.socket, path: str, logger: TransferLogger) -> None:
    file_size = Path(path).stat().st_size
    header = _pack_header(logger.transfer_id, file_size, logger.scenario, logger.mode)
    conn.sendall(header)

    logger.start()
    bytes_sent = 0
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            conn.sendall(chunk)
            bytes_sent += len(chunk)
            logger.add_block()

    checksum = file_checksum(path)
    logger.finish(
        bytes_sent=bytes_sent,
        bytes_received=0,
        window_size=1,
        file_checksum=checksum,
        status="success",
    )


def receive_file(conn: socket.socket, dest_dir: str) -> dict:
    hdr = _unpack_header(_recv_exact(conn, HEADER_SIZE))

    logger = TransferLogger(
        role="server",
        mode=hdr["mode"],
        scenario=hdr["scenario"],
        file_size=hdr["file_size"],
        transfer_id=hdr["transfer_id"],
    )

    dest = Path(dest_dir) / f"{hdr['transfer_id']}.bin"
    dest.parent.mkdir(parents=True, exist_ok=True)

    logger.start()
    bytes_received = 0
    remaining = hdr["file_size"]
    with open(dest, "wb") as f:
        while remaining > 0:
            chunk = conn.recv(min(CHUNK_SIZE, remaining))
            if not chunk:
                break
            f.write(chunk)
            bytes_received += len(chunk)
            remaining -= len(chunk)
            logger.add_block()

    status = "success" if bytes_received == hdr["file_size"] else "error"
    checksum = file_checksum(str(dest)) if status == "success" else None
    logger.finish(
        bytes_sent=0,
        bytes_received=bytes_received,
        window_size=1,
        file_checksum=checksum,
        status=status,
    )
    return {"path": str(dest), "header": hdr, "bytes_received": bytes_received, "status": status}
