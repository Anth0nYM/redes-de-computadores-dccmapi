"""Go-Back-N protocol implementation for SimPy."""

from collections import deque
from src.sim.channel import NetworkChannel


class GBNSender:
    """Go-Back-N sender with sliding window."""

    def __init__(self, window_size: int = 8, timeout_ms: float = 500):
        self.window_size = window_size
        self.timeout_ms = timeout_ms
        self.seq_num = 0
        self.base = 0
        self.window = {}
        self.timers = {}

    def get_next_packet(self, block_num: int, data: bytes = b"") -> dict | None:
        """Get the next packet to send, or None if window is full."""
        if self.seq_num - self.base >= self.window_size:
            return None

        pkt = {
            "seq": self.seq_num,
            "block": block_num,
            "data": data,
        }
        self.window[self.seq_num] = pkt
        self.timers[self.seq_num] = 0.0
        self.seq_num += 1

        return pkt

    def can_send_next(self) -> bool:
        """Check if sender can send another packet."""
        return self.seq_num - self.base < self.window_size

    def receive_ack(self, ack_num: int):
        """Process received ACK (cumulative)."""
        if ack_num >= self.base:
            # Remove all packets up to and including ack_num
            for seq in list(self.window.keys()):
                if seq <= ack_num:
                    del self.window[seq]
                    if seq in self.timers:
                        del self.timers[seq]
            self.base = ack_num + 1

    def get_window_packets(self) -> list:
        """Get all packets in current window for retransmission."""
        return [self.window[seq] for seq in sorted(self.window.keys())]


class GBNReceiver:
    """Go-Back-N receiver with cumulative ACKs."""

    def __init__(self):
        self.expected_seq = 0
        self.last_ack = -1

    def receive_packet(self, seq_num: int, data: bytes = b""):
        """Receive a packet and update expected sequence."""
        if seq_num == self.expected_seq:
            self.expected_seq += 1
            self.last_ack = seq_num

    def get_ack(self) -> int:
        """Get the cumulative ACK number."""
        return self.last_ack


class GBNProtocol:
    """End-to-end GBN protocol simulation."""

    def __init__(
        self,
        window_size: int = 8,
        timeout_ms: float = 500,
        mean_delay_ms: float = 50,
        loss_rate: float = 0.271,
        jitter_ms: float = 0,
    ):
        self.sender = GBNSender(window_size, timeout_ms)
        self.receiver = GBNReceiver()
        self.channel = NetworkChannel(mean_delay_ms, loss_rate, jitter_ms)
        self.retrans_count = 0

    def transfer(self, data: bytes, block_size: int = 1024) -> tuple[int, int]:
        """
        Transfer data using GBN protocol.

        Returns:
            (total_bytes_transferred, retransmission_count)
        """
        num_blocks = (len(data) + block_size - 1) // block_size
        blocks = [
            data[i * block_size : (i + 1) * block_size]
            for i in range(num_blocks)
        ]

        # Simple simulation without SimPy (synchronous model)
        block_idx = 0
        acked_blocks = 0

        while acked_blocks < num_blocks:
            # Send packets up to window size
            while (
                block_idx < num_blocks
                and self.sender.can_send_next()
            ):
                pkt = self.sender.get_next_packet(block_idx, blocks[block_idx])
                if not self.channel.should_drop():
                    self.receiver.receive_packet(pkt["seq"], pkt["data"])
                block_idx += 1

            # Get cumulative ACK from receiver
            ack = self.receiver.get_ack()
            if ack >= 0:
                self.sender.receive_ack(ack)
                acked_blocks = ack + 1

        return len(data), self.retrans_count
