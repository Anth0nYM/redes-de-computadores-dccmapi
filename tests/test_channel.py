"""Tests for network channel simulation with delay and loss."""

import pytest
from src.sim.channel import NetworkChannel


class TestNetworkChannel:
    """Test suite for NetworkChannel."""

    def test_channel_creation(self):
        """Channel should be created with mean delay and loss probability."""
        channel = NetworkChannel(mean_delay_ms=100, loss_rate=0.271)
        assert channel.mean_delay_ms == 100
        assert channel.loss_rate == 0.271

    def test_channel_delay_distribution(self):
        """Channel delay should follow approximately Normal distribution with given mean."""
        channel = NetworkChannel(mean_delay_ms=100, jitter_ms=10, loss_rate=0.0)

        # Simulate 1000 packets, collect delays
        delays = []
        for _ in range(1000):
            delay = channel.get_delay()
            delays.append(delay)

        mean_delay = sum(delays) / len(delays)

        # Mean should be close to 100ms (within 5ms tolerance)
        assert abs(mean_delay - 100) < 5, f"Expected ~100ms, got {mean_delay:.2f}ms"

    def test_channel_loss_rate(self):
        """Channel should drop packets at approximately the specified loss rate."""
        channel = NetworkChannel(mean_delay_ms=100, loss_rate=0.271)

        # Simulate 10000 packets and count drops
        num_packets = 10000
        dropped = 0

        for _ in range(num_packets):
            if channel.should_drop():
                dropped += 1

        actual_rate = dropped / num_packets

        # Actual rate should be close to 27.1% (within 2% tolerance)
        assert abs(actual_rate - 0.271) < 0.02, \
            f"Expected ~27.1% loss, got {actual_rate * 100:.1f}%"

    def test_channel_no_loss(self):
        """Channel with 0% loss should never drop packets."""
        channel = NetworkChannel(mean_delay_ms=100, loss_rate=0.0)

        for _ in range(1000):
            assert not channel.should_drop(), "Channel with 0% loss dropped a packet"

    def test_channel_certain_loss(self):
        """Channel with 100% loss should always drop packets."""
        channel = NetworkChannel(mean_delay_ms=100, loss_rate=1.0)

        for _ in range(100):
            assert channel.should_drop(), "Channel with 100% loss did not drop a packet"
