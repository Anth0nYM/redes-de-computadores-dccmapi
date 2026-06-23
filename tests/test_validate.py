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

        # Calibrated against real RUDP (0.676s, 0 retx).
        assert 0.5 < result["time_mean_s"] < 0.85, \
            f"Scenario A time: expected ~0.676s, got {result['time_mean_s']:.3f}s"

        # No retransmissions without loss.
        assert result["retx_mean"] < 1, \
            f"Scenario A should have ~0 retransmissions, got {result['retx_mean']:.1f}"

    def test_scenario_b_medium_loss(self):
        """Scenario B: Medium loss."""
        validator = CalibrationValidator()

        # Real RUDP data: time_mean_s=53.165, retx_mean=91.1
        result = validator.run_scenario_b()

        assert "time_mean_s" in result
        assert "retx_mean" in result

        # Calibrated against real RUDP (53.2s, 91.1 retx).
        assert 40 < result["time_mean_s"] < 65, \
            f"Scenario B time: expected ~53.2s, got {result['time_mean_s']:.1f}s"
        assert 75 < result["retx_mean"] < 115, \
            f"Scenario B retx: expected ~91.1, got {result['retx_mean']:.1f}"

    def test_scenario_c_high_loss(self):
        """Scenario C: High loss."""
        validator = CalibrationValidator()

        # Real RUDP data: time_mean_s=144.613, retx_mean=238.5
        result = validator.run_scenario_c()

        assert "time_mean_s" in result
        assert "retx_mean" in result

        # Calibrated against real RUDP (144.6s, 238.5 retx).
        assert 100 < result["time_mean_s"] < 165, \
            f"Scenario C time: expected ~144.6s, got {result['time_mean_s']:.1f}s"
        assert 210 < result["retx_mean"] < 280, \
            f"Scenario C retx: expected ~238.5, got {result['retx_mean']:.1f}"

    def test_calibration_report(self):
        """Should generate comparison table."""
        validator = CalibrationValidator()
        report = validator.generate_report()

        assert "A" in report
        assert "B" in report
        assert "C" in report
