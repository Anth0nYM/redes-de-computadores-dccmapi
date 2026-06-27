"""Tests for the stress-scenario forecast (D8, task 8).

Task 8 asks to *forecast* the transfer time under 25% raw packet loss. The tc
loss is the raw per-packet drop; the simulator consumes the effective per-block
loss after 3 IP fragments, p_eff = 1-(1-p)^3. The forecast must be coherent
with the measured anchors: at C's raw loss (20%) the prediction reproduces the
real C time, and the 25% stress sits above C on the monotone loss->time curve.
"""

import pytest

from src.sim.stress import effective_loss, forecast_time, StressForecast
from src.sim.validate import REAL_DATA


class TestEffectiveLoss:
    """Raw tc loss -> effective per-block loss over 3 IP fragments."""

    def test_matches_three_fragment_formula(self):
        assert effective_loss(0.25) == pytest.approx(1 - 0.75 ** 3)

    def test_zero_loss_stays_zero(self):
        assert effective_loss(0.0) == 0.0

    def test_monotonic_in_raw_loss(self):
        assert effective_loss(0.25) > effective_loss(0.20) > effective_loss(0.10)


class TestForecastTime:
    """A single forecast point: mean/std and a bootstrap CI over >=30 reps."""

    def test_reports_at_least_30_reps_and_valid_ci(self):
        f = forecast_time(raw_loss=0.25, reps=30, seed=1)
        assert f["n"] >= 30
        assert f["mean"] > 0
        assert f["ci_lo"] <= f["mean"] <= f["ci_hi"]

    def test_anchor_reproduces_real_c(self):
        """At C's raw loss (20%) and delay, the forecast must match real C."""
        f = forecast_time(raw_loss=0.20, reps=30, seed=1)
        real_c = REAL_DATA["C"]["time_mean_s"]
        assert f["mean"] == pytest.approx(real_c, rel=0.20)


class TestStressForecastCoherence:
    """The 25% stress prediction must be coherent with the C anchor."""

    def test_stress_exceeds_scenario_c(self):
        sf = StressForecast(reps=30, seed=1)
        report = sf.forecast()
        real_c = REAL_DATA["C"]["time_mean_s"]
        assert report["stress"]["mean"] > real_c, (
            f"25% stress {report['stress']['mean']:.1f}s should exceed "
            f"real C {real_c:.1f}s"
        )

    def test_forecast_monotone_in_loss(self):
        sf = StressForecast(reps=30, seed=1)
        report = sf.forecast()
        means = [report[k]["mean"] for k in ("c_anchor", "stress")]
        assert means[1] > means[0]
