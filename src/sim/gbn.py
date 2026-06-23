"""Go-Back-N protocol: abstract sender/receiver plus a SimPy event-driven engine.

The Fase 2 deliverable is a discrete-event simulator (per the project spec:
"simulador de eventos discretos que espelhe o comportamento do sistema R-UDP").
``GBNProtocol`` therefore runs the transfer inside a ``simpy.Environment``:
data packets, ACKs and the retransmission timeout are real scheduled events,
so transfer time and retransmission counts emerge from the event timeline
rather than from a synchronous round approximation.

``GBNSender`` / ``GBNReceiver`` keep the abstract sliding-window logic used by
the unit tests; the SimPy engine drives its own sender/receiver state.
"""

import simpy

from src.sim.channel import NetworkChannel


class GBNSender:
    """Go-Back-N sender with sliding window (abstract logic for unit tests)."""

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
    """Go-Back-N receiver with cumulative ACKs (abstract logic for unit tests)."""

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


class _GBNEngine:
    """Discrete-event Go-Back-N transfer over a lossy channel.

    Textbook GBN: a single retransmission timer guards the oldest unacked
    packet (``base``). Cumulative ACKs slide the window and reset the timer;
    when the timer fires the sender goes back to N and retransmits the window.
    Data packets are subject to Bernoulli loss; ACKs are delivered reliably
    (the cumulative-ACK semantics already recover from late ACKs, and the
    scenario loss rate is the effective per-block loss from the paper).
    """

    def __init__(
        self,
        env: simpy.Environment,
        num_blocks: int,
        window_size: int,
        timeout_s: float,
        channel: NetworkChannel,
    ):
        self.env = env
        self.num_blocks = num_blocks
        self.window = window_size
        self.timeout_s = timeout_s
        self.channel = channel

        # Sender state.
        self.base = 0
        self.next_seq = 0
        self.retrans_count = 0

        # Receiver state.
        self.expected = 0

        # Event the sender waits on; an advancing ACK fires it.
        self.ack_event = None

        # FIFO link state: latest arrival time per direction. A real link does
        # not reorder packets sent back-to-back, even when the per-packet delay
        # varies (jitter); clamping arrivals to be monotonic enforces that.
        self._last_data_arrival = 0.0
        self._last_ack_arrival = 0.0

        self.done = env.event()
        self.sender_proc = env.process(self._sender())

    def _one_way_delay_s(self) -> float:
        """Sample a one-way propagation delay (ms -> s, never negative)."""
        return max(0.0, self.channel.get_delay() / 1000.0)

    def _sender(self):
        """Sender process: fill the window, then wait for ACK or timeout."""
        while self.base < self.num_blocks:
            # Send every packet the window currently allows.
            while (
                self.next_seq < self.base + self.window
                and self.next_seq < self.num_blocks
            ):
                self._send_data(self.next_seq)
                self.next_seq += 1

            # Wait for the retransmission timer or an advancing ACK, whichever
            # comes first. A fresh ack_event per iteration avoids same-instant
            # races when a whole window of ACKs arrives together.
            self.ack_event = self.env.event()
            timeout_ev = self.env.timeout(self.timeout_s)
            yield self.ack_event | timeout_ev

            if not self.ack_event.triggered:
                # Timer fired with no progress: go back to N.
                self.retrans_count += 1
                self.next_seq = self.base
            # Otherwise an ACK advanced the window; loop resets the timer.

        if not self.done.triggered:
            self.done.succeed()

    def _send_data(self, seq: int):
        """Transmit one data packet through the lossy, FIFO channel."""
        if self.channel.should_drop():
            return  # lost in flight: no delivery event scheduled
        arrival = max(self.env.now + self._one_way_delay_s(), self._last_data_arrival)
        self._last_data_arrival = arrival
        self.env.process(self._deliver_data(seq, arrival))

    def _deliver_data(self, seq: int, arrival: float):
        """Channel process: deliver a data packet at its FIFO arrival time."""
        yield self.env.timeout(arrival - self.env.now)
        self._receiver_receive(seq)

    def _receiver_receive(self, seq: int):
        """Receiver: accept in-order packets, always (re)send a cumulative ACK."""
        if seq == self.expected:
            self.expected += 1
        ack_num = self.expected - 1  # highest in-order block received
        if ack_num >= 0:
            arrival = max(
                self.env.now + self._one_way_delay_s(), self._last_ack_arrival
            )
            self._last_ack_arrival = arrival
            self.env.process(self._deliver_ack(ack_num, arrival))

    def _deliver_ack(self, ack_num: int, arrival: float):
        """Channel process: deliver a cumulative ACK at its FIFO arrival time."""
        yield self.env.timeout(arrival - self.env.now)
        self._sender_receive_ack(ack_num)

    def _sender_receive_ack(self, ack_num: int):
        """Sender: slide the window on a cumulative ACK and wake the sender."""
        if ack_num >= self.base:
            self.base = ack_num + 1
            if self.base >= self.num_blocks and not self.done.triggered:
                self.done.succeed()
            # Wake the sender once; same-instant ACKs already advanced base.
            if self.ack_event is not None and not self.ack_event.triggered:
                self.ack_event.succeed()


class GBNProtocol:
    """End-to-end GBN transfer driven by a SimPy discrete-event simulation."""

    def __init__(
        self,
        window_size: int = 8,
        timeout_ms: float = 500,
        mean_delay_ms: float = 50,
        loss_rate: float = 0.271,
        jitter_ms: float = 0,
    ):
        self.window_size = window_size
        self.timeout_ms = timeout_ms
        self.channel = NetworkChannel(mean_delay_ms, loss_rate, jitter_ms)
        self.retrans_count = 0
        self.elapsed_s = 0.0

    def transfer(self, data: bytes, block_size: int = 1024) -> tuple[int, int]:
        """
        Transfer ``data`` using Go-Back-N inside a SimPy environment.

        Side effects:
            self.retrans_count -- timeout/retransmission events.
            self.elapsed_s      -- simulated wall-clock time (env.now at done).

        Returns:
            (total_bytes_transferred, retransmission_count)
        """
        num_blocks = (len(data) + block_size - 1) // block_size

        env = simpy.Environment()
        engine = _GBNEngine(
            env=env,
            num_blocks=num_blocks,
            window_size=self.window_size,
            timeout_s=self.timeout_ms / 1000.0,
            channel=self.channel,
        )
        env.run(until=engine.done)

        self.retrans_count = engine.retrans_count
        self.elapsed_s = env.now
        return len(data), self.retrans_count
