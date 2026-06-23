"""Tests for the throughput-vs-filesize curve (D5, task 4)."""

import pytest
from src.sim.throughput import (
    theoretical_throughput_KBps,
    measure_throughput_KBps,
    ThroughputCurve,
)


class TestTheoreticalThroughput:
    """The window-limited throughput ceiling."""

    def test_formula(self):
        """Ceiling = window * block_size / RTT (expressed in KBps)."""
        # window 8, block 4096 B, RTT 20 ms -> 8*4096/0.02 = 1.6384 MB/s.
        tput = theoretical_throughput_KBps(window=8, block_size=4096, rtt_s=0.02)
        assert tput == pytest.approx(8 * 4096 / 0.02 / 1024, rel=1e-9)

    def test_ceiling_scales_with_window(self):
        """A larger window raises the ceiling proportionally."""
        small = theoretical_throughput_KBps(4, 4096, 0.02)
        large = theoretical_throughput_KBps(16, 4096, 0.02)
        assert large == pytest.approx(4 * small)


class TestMeasuredThroughput:
    """Throughput measured from the SimPy engine."""

    def test_below_ceiling(self):
        """Measured throughput never exceeds the theoretical ceiling."""
        ceiling = theoretical_throughput_KBps(8, 4096, 0.02)
        tput = measure_throughput_KBps(size_mb=1, scenario="A", reps=3)
        assert tput <= ceiling + 1e-6, \
            f"Throughput {tput:.1f} exceeded ceiling {ceiling:.1f}"

    def test_increases_with_size(self):
        """Larger files amortize the setup RTT, so throughput rises."""
        small = measure_throughput_KBps(size_mb=1, scenario="A", reps=3)
        large = measure_throughput_KBps(size_mb=50, scenario="A", reps=3)
        assert large > small, \
            f"Expected throughput to rise: 1MB={small:.1f}, 50MB={large:.1f}"

    def test_saturates_near_ceiling(self):
        """A large file should saturate within a few percent of the ceiling."""
        ceiling = theoretical_throughput_KBps(8, 4096, 0.02)
        tput = measure_throughput_KBps(size_mb=50, scenario="A", reps=3)
        assert tput >= 0.95 * ceiling, \
            f"50MB throughput {tput:.1f} far below ceiling {ceiling:.1f}"


class TestThroughputCurve:
    """The full sweep used to build the figure."""

    def test_curve_monotonic_nondecreasing(self):
        """The curve should not decrease as file size grows (clean channel)."""
        curve = ThroughputCurve(scenario="A", sizes_mb=[1, 5, 25], reps=3)
        sizes, tputs = curve.compute()
        assert sizes == [1, 5, 25]
        for earlier, later in zip(tputs, tputs[1:]):
            assert later >= earlier - 1.0  # allow tiny jitter noise
