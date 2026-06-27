"""Tests for the jitter-impact study (D7, task 7).

The hypothesis: a larger delay jitter (std of the per-packet propagation delay)
widens the distribution of the total transfer time, i.e. the run-to-run
variance grows monotonically with the jitter. The channel is kept clean
(scenario A, no loss) so the variance is jitter-driven, not loss-driven.
"""

import random

import pytest

from src.sim.jitter_sweep import measure_time_stats, JitterSweep


class TestMeasureTimeStats:
    """One operating point: mean and std of the transfer time over reps."""

    def test_returns_nonnegative_mean_and_std(self):
        mean, std = measure_time_stats(jitter_ms=10, reps=20, seed=1)
        assert mean > 0
        assert std >= 0

    def test_more_jitter_raises_variance(self):
        """Higher jitter must widen the transfer-time distribution."""
        _, std_low = measure_time_stats(jitter_ms=2, reps=40, seed=1)
        _, std_high = measure_time_stats(jitter_ms=60, reps=40, seed=1)
        assert std_high > std_low, (
            f"Expected variance to grow with jitter: "
            f"std(2ms)={std_low:.5f} vs std(60ms)={std_high:.5f}"
        )


class TestJitterSweep:
    """The full sweep used to build the figure."""

    def test_sweep_returns_aligned_series(self):
        sweep = JitterSweep(jitters=[1, 10, 40], reps=20, seed=1)
        jitters, means, stds = sweep.compute()
        assert len(jitters) == len(means) == len(stds) == 3
        assert all(s >= 0 for s in stds)

    def test_variance_increases_across_sweep(self):
        sweep = JitterSweep(jitters=[1, 5, 10, 20, 40, 80], reps=40, seed=1)
        assert sweep.variance_increases(), (
            f"std series not increasing: {sweep.compute()[2]}"
        )

    def test_endpoints_clearly_separated(self):
        """The widest jitter should dwarf the narrowest in variance."""
        sweep = JitterSweep(jitters=[1, 80], reps=40, seed=1)
        _, _, stds = sweep.compute()
        assert stds[-1] > 5 * stds[0]
