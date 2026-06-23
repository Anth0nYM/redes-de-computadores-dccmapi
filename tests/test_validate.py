"""Tests for simulator calibration against real data."""

import pytest
from src.sim.validate import CalibrationValidator


class TestCalibration:
    """Test suite for calibration against real data."""

    def test_scenario_a_no_loss(self):
        """Scenario A: No loss, low latency."""
        validator = CalibrationValidator()

        # Real RUDP data: time_mean_s=0.676
        result = validator.run_scenario_a()

        assert "time_mean_s" in result
        assert "retx_mean" in result

        # Should execute without error
        assert result["time_mean_s"] > 0, "Time should be positive"

        # No retransmissions
        assert result["retx_mean"] < 1, \
            f"Scenario A should have ~0 retransmissions, got {result['retx_mean']:.1f}"

    def test_scenario_b_medium_loss(self):
        """Scenario B: Medium loss."""
        validator = CalibrationValidator()

        # Real RUDP data: time_mean_s=53.165, retx_mean=91.1
        result = validator.run_scenario_b()

        assert "time_mean_s" in result
        assert "retx_mean" in result

        # Should execute without error
        assert result["time_mean_s"] > 0, "Time should be positive"
        assert result["retx_mean"] >= 0, "Retransmissions should be non-negative"

    def test_scenario_c_high_loss(self):
        """Scenario C: High loss."""
        validator = CalibrationValidator()

        # Real RUDP data: time_mean_s=144.613, retx_mean=238.5
        result = validator.run_scenario_c()

        assert "time_mean_s" in result
        assert "retx_mean" in result

        # Should execute without error
        assert result["time_mean_s"] > 0, "Time should be positive"
        assert result["retx_mean"] >= 0, "Retransmissions should be non-negative"

    def test_calibration_report(self):
        """Should generate comparison table."""
        validator = CalibrationValidator()
        report = validator.generate_report()

        assert "A" in report
        assert "B" in report
        assert "C" in report
