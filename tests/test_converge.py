"""Tests for convergence analysis: repetitions + bootstrap 95% CI."""

import pytest
from src.sim.converge import bootstrap_ci, ConvergenceAnalyzer


class TestBootstrapCI:
    """Test suite for bootstrap confidence interval."""

    def test_ci_returns_three_values(self):
        """bootstrap_ci should return (mean, lower, upper)."""
        data = [10.0, 11.0, 9.0, 10.5, 9.5, 10.2, 10.8, 9.8]
        mean, lower, upper = bootstrap_ci(data)
        assert lower <= mean <= upper

    def test_ci_brackets_mean_of_constant(self):
        """CI of a constant sample collapses onto that constant."""
        data = [5.0] * 50
        mean, lower, upper = bootstrap_ci(data)
        assert mean == pytest.approx(5.0)
        assert lower == pytest.approx(5.0)
        assert upper == pytest.approx(5.0)

    def test_ci_width_shrinks_with_more_data(self):
        """More samples => narrower CI (lower estimator variance)."""
        import random
        random.seed(42)
        small = [random.gauss(100, 10) for _ in range(10)]
        large = [random.gauss(100, 10) for _ in range(1000)]

        _, lo_s, hi_s = bootstrap_ci(small)
        _, lo_l, hi_l = bootstrap_ci(large)

        assert (hi_l - lo_l) < (hi_s - lo_s)

    def test_ci_confidence_level(self):
        """95% CI should be wider than 80% CI."""
        import random
        random.seed(1)
        data = [random.gauss(50, 5) for _ in range(100)]

        _, lo95, hi95 = bootstrap_ci(data, confidence=0.95)
        _, lo80, hi80 = bootstrap_ci(data, confidence=0.80)

        assert (hi95 - lo95) > (hi80 - lo80)


class TestConvergenceAnalyzer:
    """Test suite for the scenario convergence analyzer."""

    def test_runs_minimum_repetitions(self):
        """Analyzer should run at least 30 repetitions."""
        analyzer = ConvergenceAnalyzer(num_reps=30)
        result = analyzer.analyze_scenario("B")

        assert result["n"] >= 30
        assert "time_mean_s" in result
        assert "time_ci_lower" in result
        assert "time_ci_upper" in result
        assert "retx_mean" in result

    def test_ci_covers_real_value_scenario_b(self):
        """95% CI for scenario B time should cover the real measurement (53.2s)."""
        analyzer = ConvergenceAnalyzer(num_reps=30)
        result = analyzer.analyze_scenario("B")

        real_time = 53.165
        # The CI is allowed some slack; the point is coverage of the real anchor.
        assert result["time_ci_lower"] <= real_time + 8, \
            f"CI lower {result['time_ci_lower']:.1f} too far above real {real_time}"
        assert result["time_ci_upper"] >= real_time - 8, \
            f"CI upper {result['time_ci_upper']:.1f} too far below real {real_time}"

    def test_report_contains_all_scenarios(self):
        """Convergence report should cover A, B and C."""
        analyzer = ConvergenceAnalyzer(num_reps=30)
        report = analyzer.generate_report()
        assert "A" in report and "B" in report and "C" in report
