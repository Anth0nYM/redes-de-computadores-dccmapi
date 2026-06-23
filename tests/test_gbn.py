"""Tests for Go-Back-N protocol implementation."""

import pytest
from src.sim.gbn import GBNSender, GBNReceiver, GBNProtocol


class TestGBNProtocol:
    """Test suite for Go-Back-N protocol."""

    def test_gbn_sender_creation(self):
        """Sender should be created with window size and timeout."""
        sender = GBNSender(window_size=8, timeout_ms=500)
        assert sender.window_size == 8
        assert sender.timeout_ms == 500
        assert sender.seq_num == 0

    def test_gbn_receiver_creation(self):
        """Receiver should be created with initial sequence number."""
        receiver = GBNReceiver()
        assert receiver.expected_seq == 0

    def test_gbn_transfer_no_loss(self):
        """Should transfer 256 blocks without loss or retransmission."""
        protocol = GBNProtocol(
            window_size=8,
            timeout_ms=500,
            mean_delay_ms=50,
            loss_rate=0.0
        )

        # Transfer 256 blocks (256 * 1024 bytes = 256 KB)
        num_blocks = 256
        data = b"X" * (num_blocks * 1024)

        total_data, retrans_count = protocol.transfer(data, block_size=1024)

        # Should transfer all data
        assert total_data == len(data), f"Expected {len(data)} bytes, got {total_data}"

        # No loss = 0 retransmissions
        assert retrans_count == 0, f"Expected 0 retransmissions, got {retrans_count}"

    def test_gbn_cumulative_ack(self):
        """ACK should be cumulative (one ACK for multiple packets)."""
        sender = GBNSender(window_size=8, timeout_ms=500)

        # Send 8 packets in window
        packets_sent = []
        for i in range(8):
            pkt = sender.get_next_packet(block_num=i)
            packets_sent.append(pkt)

        assert len(packets_sent) == 8

        # Receiver receives and sends cumulative ACK for packet 7
        # (implying it got 0-7)
        receiver = GBNReceiver()
        for i in range(8):
            receiver.receive_packet(packets_sent[i]["seq"], packets_sent[i]["data"])

        # ACK should be for packet 7 (0-indexed)
        ack = receiver.get_ack()
        assert ack == 7, f"Expected ACK 7, got {ack}"

    def test_gbn_out_of_order_rejected(self):
        """Receiver should reject out-of-order packets."""
        receiver = GBNReceiver()

        # Try to receive packet 5 when expecting 0
        receiver.receive_packet(seq_num=5, data=b"data")

        # ACK should still be for packet -1 (expecting 0)
        ack = receiver.get_ack()
        assert ack == -1, f"Expected ACK -1 (no valid packets yet), got {ack}"

    def test_gbn_window_size(self):
        """Sender should not send more than window_size packets outstanding."""
        sender = GBNSender(window_size=3, timeout_ms=500)

        # Send 3 packets (fills window)
        for i in range(3):
            pkt = sender.get_next_packet(block_num=i)
            assert pkt is not None

        # Window is full, next packet should be held until ACK
        can_send = sender.can_send_next()
        assert not can_send, "Sender should not allow packet when window is full"
