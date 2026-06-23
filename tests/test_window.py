"""Tests for the window-sensitivity curve (D6, task 5)."""

import pytest
from src.sim.window_sweep import (
    theoretical_knee_N,
    measure_throughput_for_window,
    WindowSweep,
)

# Study fixture: clean channel (scenario A, RTT 20 ms), 2000 KB/s bottleneck.
# BDP/block = 2000 * 1024 * 0.02 / 4096 = 10 -> knee at N = 10.
BW = 2000.0
RTT = 0.02


class TestTheoreticalKnee:
    """The window that fills the pipe: N* = BDP / block."""

    def test_knee_formula(self):
        knee = theoretical_knee_N(bandwidth_KBps=BW, rtt_s=RTT, block_size=4096)
        assert knee == pytest.approx(10.0)

    def test_knee_scales_with_bandwidth(self):
        low = theoretical_knee_N(1000, RTT, 4096)
        high = theoretical_knee_N(4000, RTT, 4096)
        assert high == pytest.approx(4 * low)


class TestMeasuredWindow:
    """Throughput as a function of the window size N."""

    def test_below_knee_is_window_limited(self):
        """For N below the knee, throughput grows with N (window-limited)."""
        t2 = measure_throughput_for_window(2, bandwidth_KBps=BW, reps=3)
        t6 = measure_throughput_for_window(6, bandwidth_KBps=BW, reps=3)
        assert t6 > t2, f"Expected growth below knee: N2={t2:.0f}, N6={t6:.0f}"

    def test_above_knee_saturates(self):
        """Beyond the knee, more window does not raise throughput (link-limited)."""
        t16 = measure_throughput_for_window(16, bandwidth_KBps=BW, reps=3)
        t32 = measure_throughput_for_window(32, bandwidth_KBps=BW, reps=3)
        # Both saturated at ~bandwidth; the extra window buys almost nothing.
        assert t32 <= t16 * 1.05
        assert t16 >= 0.9 * BW, f"N16 throughput {t16:.0f} not near link rate {BW}"

    def test_never_exceeds_bandwidth(self):
        """Throughput is capped by the link rate."""
        t32 = measure_throughput_for_window(32, bandwidth_KBps=BW, reps=3)
        assert t32 <= BW * 1.02


class TestWindowSweep:
    """The full sweep used to build the figure and locate the knee."""

    def test_sweep_has_knee_near_theory(self):
        sweep = WindowSweep(
            bandwidth_KBps=BW,
            windows=[1, 2, 4, 6, 8, 10, 12, 16, 24, 32],
            reps=3,
        )
        windows, tputs = sweep.compute()
        assert windows[0] == 1

        knee_theory = sweep.knee_N()
        knee_measured = sweep.measured_knee_N()
        # The empirical knee should land within a couple of blocks of BDP/block.
        assert abs(knee_measured - knee_theory) <= 2, \
            f"Measured knee {knee_measured} far from theory {knee_theory:.1f}"
