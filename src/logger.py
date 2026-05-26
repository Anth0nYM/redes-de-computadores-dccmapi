import json
import os
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(os.environ.get("LOG_DIR", "/app/logs/app"))


@dataclass
class TransferRecord:
    transfer_id: str      # UUID shared by client and server for the same transfer
    role: str             # "client" | "server"
    mode: str             # "TCP" | "RUDP"
    scenario: str         # "A" | "B" | "C"
    file_size: int        # bytes — size of the file being transferred
    start_time: str       # ISO 8601 UTC
    end_time: str         # ISO 8601 UTC
    transfer_time_s: float
    bytes_sent: int
    bytes_received: int
    throughput_bytes_s: float  # bytes_sent/s for client, bytes_received/s for server
    num_blocks: int            # total data blocks produced by the sender
    num_retransmissions: int
    num_acks: int
    num_timeouts: int
    window_size: int           # sliding window size (1 for TCP, N for Go-Back-N)
    file_checksum: str | None  # hex digest of the complete file; None if interrupted
    status: str                # "success" | "error"


class TransferLogger:
    """
    Collects per-transfer metrics and appends one JSON line to LOG_FILE when
    finish() is called. Thread-safe for sequential use; not designed for
    concurrent transfers writing to the same file simultaneously.

    Usage:
        # client side — generates the transfer_id
        log = TransferLogger(role="client", mode="TCP", scenario="A", file_size=n)
        # server side — reuses the transfer_id received from the client
        log = TransferLogger(role="server", mode="TCP", scenario="A", file_size=n,
                             transfer_id="<uuid from client>")

        log.start()
        log.add_block(); log.add_ack(); log.add_retransmission(); log.add_timeout()
        record = log.finish(bytes_sent=n, bytes_received=n,
                            window_size=1, file_checksum="...", status="success")
    """

    def __init__(
        self,
        role: str,
        mode: str,
        scenario: str,
        file_size: int,
        transfer_id: str | None = None,
    ) -> None:
        self.transfer_id = transfer_id or str(uuid.uuid4())
        self.role = role
        self.mode = mode
        self.scenario = scenario
        self.file_size = file_size
        self.num_blocks = 0
        self.num_retransmissions = 0
        self.num_acks = 0
        self.num_timeouts = 0
        self._start_monotonic: float | None = None
        self._start_wall: datetime | None = None

    def start(self) -> None:
        self._start_monotonic = time.monotonic()
        self._start_wall = datetime.now(timezone.utc)

    def add_block(self) -> None:
        self.num_blocks += 1

    def add_retransmission(self) -> None:
        self.num_retransmissions += 1

    def add_ack(self) -> None:
        self.num_acks += 1

    def add_timeout(self) -> None:
        self.num_timeouts += 1

    def finish(
        self,
        bytes_sent: int,
        bytes_received: int,
        window_size: int,
        file_checksum: str | None,
        status: str = "success",
    ) -> TransferRecord:
        if self._start_monotonic is None or self._start_wall is None:
            raise RuntimeError("start() must be called before finish()")

        end_wall = datetime.now(timezone.utc)
        transfer_time_s = time.monotonic() - self._start_monotonic
        data_bytes = bytes_sent if self.role == "client" else bytes_received
        throughput = data_bytes / transfer_time_s if transfer_time_s > 0 else 0.0

        record = TransferRecord(
            transfer_id=self.transfer_id,
            role=self.role,
            mode=self.mode,
            scenario=self.scenario,
            file_size=self.file_size,
            start_time=self._start_wall.isoformat(),
            end_time=end_wall.isoformat(),
            transfer_time_s=round(transfer_time_s, 6),
            bytes_sent=bytes_sent,
            bytes_received=bytes_received,
            throughput_bytes_s=round(throughput, 2),
            num_blocks=self.num_blocks,
            num_retransmissions=self.num_retransmissions,
            num_acks=self.num_acks,
            num_timeouts=self.num_timeouts,
            window_size=window_size,
            file_checksum=file_checksum,
            status=status,
        )
        _append(record, self.role)
        return record


def _append(record: TransferRecord, role: str) -> None:
    # separate files per role to avoid concurrent append races on the shared Docker volume
    log_file = LOG_DIR / f"{role}_transfers.jsonl"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a") as f:
        f.write(json.dumps(asdict(record)) + "\n")
