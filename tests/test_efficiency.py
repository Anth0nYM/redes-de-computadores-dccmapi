"""Tests for the efficiency study (D9, task 9: razao DATA/ACK).

In Go-Back-N the receiver emits one cumulative ACK per arriving DATA packet,
so the only DATA packets without an ACK are the ones the channel drops. The
DATA/ACK ratio therefore tracks 1/(1-p_eff): it is ~1 on a clean channel and
grows with loss, i.e. protocol efficiency degrades as loss rises.
"""

import pytest

from src.sim.efficiency import measure_efficiency, EfficiencyStudy
from src.sim.validate import SCENARIO_PARAMS


class TestMeasureEfficiency:
    """One scenario: DATA/ACK counts and their ratio over reps."""

    def test_clean_channel_ratio_is_one(self):
        eff = measure_efficiency("A", reps=10, seed=1)
        assert eff["ratio"] == pytest.approx(1.0, abs=1e-6)

    def test_counts_are_consistent(self):
        eff = measure_efficiency("B", reps=10, seed=1)
        # Every ACK answers an arriving DATA packet, so DATA >= ACK > 0.
        assert eff["data_mean"] >= eff["ack_mean"] > 0
        assert eff["ratio"] == pytest.approx(
            eff["data_mean"] / eff["ack_mean"], rel=1e-9
        )

    def test_ratio_tracks_inverse_survival(self):
        """DATA/ACK ~ 1/(1-p_eff) for the cumulative-ACK GBN receiver."""
        eff = measure_efficiency("C", reps=20, seed=1)
        p = SCENARIO_PARAMS["C"]["loss_rate"]
        assert eff["ratio"] == pytest.approx(1.0 / (1.0 - p), rel=0.10)


class TestEfficiencyStudy:
    """Across scenarios: efficiency worsens (ratio rises) with loss."""

    def test_ratio_increases_with_loss(self):
        study = EfficiencyStudy(reps=20, seed=1)
        rows = study.compute()
        ratios = [rows[s]["ratio"] for s in ("A", "B", "C")]
        assert ratios[0] < ratios[1] < ratios[2], f"not monotone: {ratios}"

    def test_clean_is_most_efficient(self):
        study = EfficiencyStudy(reps=20, seed=1)
        rows = study.compute()
        assert rows["A"]["ratio"] <= min(rows["B"]["ratio"], rows["C"]["ratio"])
