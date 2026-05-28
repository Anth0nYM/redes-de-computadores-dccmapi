import socket
import struct
import time
import zlib
from pathlib import Path

from checksum import file_checksum
from logger import TransferLogger
from tcp_transfer import (
    HEADER_SIZE as META_SIZE,
    _pack_header as _pack_meta,
    _unpack_header as _unpack_meta,
)

# ── Packet types ──────────────────────────────────────────────────────────────
PKT_DATA   = 0
PKT_ACK    = 1
PKT_SYN    = 2
PKT_SYNACK = 3
PKT_FIN    = 4
PKT_FINACK = 5

# ── RUDP packet header (16 bytes, big-endian) ─────────────────────────────────
#  B  pkt_type   — one of PKT_* above
#  B  flags      — reserved
#  H  window     — sender window size (meaningful in SYN/SYNACK only)
#  I  seq_num    — sequence number
#  I  ack_num    — cumulative ACK
#  H  data_len   — payload length in bytes
#  H  checksum   — CRC32 & 0xFFFF over (header with checksum=0) + payload
HDR_FMT  = "!BBHIIHH"
HDR_SIZE = struct.calcsize(HDR_FMT)  # 16

CHUNK_SIZE     = 4096
DEFAULT_WINDOW = 8
TIMEOUT_S      = 0.5
MAX_RETRIES    = 50
_BUF           = HDR_SIZE + max(META_SIZE, CHUNK_SIZE) + 64  # 4176


# ── Packet encoding / decoding ────────────────────────────────────────────────

def _crc(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFF


def _pack(pkt_type: int, seq_num: int, ack_num: int, window: int, payload: bytes) -> bytes:
    data_len = len(payload)
    base = struct.pack(HDR_FMT, pkt_type, 0, window, seq_num, ack_num, data_len, 0)
    chk  = _crc(base + payload)
    hdr  = struct.pack(HDR_FMT, pkt_type, 0, window, seq_num, ack_num, data_len, chk)
    return hdr + payload


def _unpack(raw: bytes) -> tuple[dict, bytes]:
    if len(raw) < HDR_SIZE:
        raise ValueError("packet too short")
    pkt_type, _, window, seq_num, ack_num, data_len, checksum = struct.unpack(
        HDR_FMT, raw[:HDR_SIZE]
    )
    payload = raw[HDR_SIZE: HDR_SIZE + data_len]
    zero = struct.pack(HDR_FMT, pkt_type, 0, window, seq_num, ack_num, data_len, 0)
    if _crc(zero + payload) != checksum:
        raise ValueError("checksum mismatch")
    return {"type": pkt_type, "window": window, "seq_num": seq_num, "ack_num": ack_num}, payload


# ── Public API ────────────────────────────────────────────────────────────────

def send_file(
    sock: socket.socket,
    addr: tuple,
    path: str,
    logger: TransferLogger,
    window_size: int = DEFAULT_WINDOW,
) -> None:
    file_size = Path(path).stat().st_size
    meta = _pack_meta(logger.transfer_id, file_size, logger.scenario, logger.mode)

    # ── SYN handshake ─────────────────────────────────────────────────────────
    syn = _pack(PKT_SYN, 0, 0, window_size, meta)
    for _ in range(MAX_RETRIES):
        sock.sendto(syn, addr)
        sock.settimeout(TIMEOUT_S)
        try:
            raw, _ = sock.recvfrom(_BUF)
            hdr, _ = _unpack(raw)
            if hdr["type"] == PKT_SYNACK:
                break
        except (socket.timeout, ValueError, OSError):
            pass
    else:
        raise RuntimeError("RUDP SYN handshake failed after max retries")

    # ── Load file into chunks ──────────────────────────────────────────────────
    chunks: list[bytes] = []
    with open(path, "rb") as f:
        while data := f.read(CHUNK_SIZE):
            chunks.append(data)
    total = len(chunks)

    # ── Go-Back-N sender ───────────────────────────────────────────────────────
    logger.start()
    base      = 0
    next_seq  = 0
    t_start: float | None = None

    while base < total:
        # fill window
        while next_seq < total and next_seq - base < window_size:
            sock.sendto(_pack(PKT_DATA, next_seq, 0, window_size, chunks[next_seq]), addr)
            logger.add_block()
            next_seq += 1

        if t_start is None:
            t_start = time.monotonic()

        remaining = max(0.001, TIMEOUT_S - (time.monotonic() - t_start))
        sock.settimeout(remaining)

        try:
            raw, _ = sock.recvfrom(_BUF)
            hdr, _ = _unpack(raw)
            if hdr["type"] == PKT_ACK and base <= hdr["ack_num"] < next_seq:
                base    = hdr["ack_num"] + 1
                t_start = None if base == next_seq else time.monotonic()
                logger.add_ack()
        except socket.timeout:
            logger.add_timeout()
            logger.add_retransmission()
            next_seq = base
            t_start  = None
        except (ValueError, OSError):
            pass

    # ── FIN handshake ─────────────────────────────────────────────────────────
    fin = _pack(PKT_FIN, next_seq, 0, 0, b"")
    for _ in range(MAX_RETRIES):
        sock.sendto(fin, addr)
        sock.settimeout(TIMEOUT_S)
        try:
            raw, _ = sock.recvfrom(_BUF)
            hdr, _ = _unpack(raw)
            if hdr["type"] == PKT_FINACK:
                break
        except (socket.timeout, ValueError, OSError):
            pass

    logger.finish(
        bytes_sent=file_size,
        bytes_received=0,
        window_size=window_size,
        file_checksum=file_checksum(path),
        status="success",
    )


def receive_file(sock: socket.socket, dest_dir: str) -> dict:
    # ── Wait for SYN (blocks until a client connects) ─────────────────────────
    sock.settimeout(None)
    while True:
        try:
            raw, client_addr = sock.recvfrom(_BUF)
            hdr, payload = _unpack(raw)
            if hdr["type"] == PKT_SYN:
                break
        except ValueError:
            pass

    meta        = _unpack_meta(payload)
    window_size = hdr["window"]

    logger = TransferLogger(
        role="server",
        mode=meta["mode"],
        scenario=meta["scenario"],
        file_size=meta["file_size"],
        transfer_id=meta["transfer_id"],
    )

    # ── SYNACK ────────────────────────────────────────────────────────────────
    sock.sendto(_pack(PKT_SYNACK, 0, 0, window_size, b""), client_addr)

    # ── Go-Back-N receiver ────────────────────────────────────────────────────
    dest = Path(dest_dir) / f"{meta['transfer_id']}.bin"
    dest.parent.mkdir(parents=True, exist_ok=True)

    expected_seq   = 0
    bytes_received = 0
    stall          = 0

    logger.start()
    sock.settimeout(1.0)

    with open(dest, "wb") as f:
        while stall < 30:
            try:
                raw, _ = sock.recvfrom(_BUF)
                stall = 0
            except socket.timeout:
                stall += 1
                # keepalive ACK: nudges a stalled sender to advance
                if expected_seq > 0:
                    sock.sendto(_pack(PKT_ACK, 0, expected_seq - 1, 0, b""), client_addr)
                continue

            try:
                hdr, data = _unpack(raw)
            except ValueError:
                continue

            if hdr["type"] == PKT_DATA:
                if hdr["seq_num"] == expected_seq and bytes_received < meta["file_size"]:
                    f.write(data)
                    bytes_received += len(data)
                    expected_seq   += 1
                    logger.add_block()
                # cumulative ACK — sent for every DATA packet (in-order or not)
                if expected_seq > 0:
                    sock.sendto(_pack(PKT_ACK, 0, expected_seq - 1, 0, b""), client_addr)
                    logger.add_ack()

            elif hdr["type"] == PKT_SYN and expected_seq == 0:
                # SYNACK was lost — client retransmitted SYN, resend SYNACK
                sock.sendto(_pack(PKT_SYNACK, 0, 0, window_size, b""), client_addr)

            elif hdr["type"] == PKT_FIN:
                sock.sendto(_pack(PKT_FINACK, 0, 0, 0, b""), client_addr)
                break

    status   = "success" if bytes_received == meta["file_size"] else "error"
    checksum = file_checksum(str(dest)) if status == "success" else None
    logger.finish(
        bytes_sent=0,
        bytes_received=bytes_received,
        window_size=window_size,
        file_checksum=checksum,
        status=status,
    )
    return {"path": str(dest), "header": meta, "bytes_received": bytes_received, "status": status}
