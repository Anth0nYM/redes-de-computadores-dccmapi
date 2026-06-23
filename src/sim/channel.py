"""Network channel simulation with delay and loss characteristics."""

import random


class NetworkChannel:
    """Simulates a network channel with delay and packet loss."""

    def __init__(self, mean_delay_ms: float, loss_rate: float, jitter_ms: float = 0):
        """
        Initialize a network channel.

        Args:
            mean_delay_ms: Mean delay in milliseconds (Normal distribution).
            loss_rate: Packet loss probability (0.0 to 1.0).
            jitter_ms: Standard deviation of delay (jitter) in milliseconds.
        """
        self.mean_delay_ms = mean_delay_ms
        self.loss_rate = loss_rate
        self.jitter_ms = jitter_ms if jitter_ms > 0 else mean_delay_ms * 0.1

    def get_delay(self) -> float:
        """Get a random delay from Normal(mean, jitter) distribution."""
        return random.gauss(self.mean_delay_ms, self.jitter_ms)

    def should_drop(self) -> bool:
        """Determine if a packet should be dropped based on loss rate."""
        return random.random() < self.loss_rate
