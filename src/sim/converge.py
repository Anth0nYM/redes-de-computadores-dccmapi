"""Convergence analysis: repetitions, mean/std and bootstrap 95% CI.

Runs the GBN simulator for >=30 repetitions per scenario and estimates a
confidence interval on the mean transfer time via the percentile bootstrap.
The acceptance criterion (D4) is that the CI brackets the real measurement
from results/tables/summary_stats.csv.
"""

import numpy as np

from src.sim.gbn import GBNProtocol
from src.sim.validate import REAL_DATA, SCENARIO_PARAMS, PAYLOAD_BYTES


def bootstrap_ci(
    data: list[float],
    confidence: float = 0.95,
    n_resamples: int = 2000,
    seed: int | None = None,
) -> tuple[float, float, float]:
    """
    Percentile bootstrap confidence interval for the mean.

    Args:
        data: observed sample.
        confidence: confidence level (e.g. 0.95 for a 95% CI).
        n_resamples: number of bootstrap resamples.
        seed: optional RNG seed for reproducibility.

    Returns:
        (mean, ci_lower, ci_upper)
    """
    arr = np.asarray(data, dtype=float)
    mean = float(arr.mean())

    rng = np.random.default_rng(seed)
    n = len(arr)
    resample_means = arr[rng.integers(0, n, size=(n_resamples, n))].mean(axis=1)

    alpha = 1.0 - confidence
    lower = float(np.percentile(resample_means, 100 * (alpha / 2)))
    upper = float(np.percentile(resample_means, 100 * (1 - alpha / 2)))
    return mean, lower, upper


class ConvergenceAnalyzer:
    """Repeats a scenario, then reports mean/std and a bootstrap 95% CI."""

    def __init__(self, num_reps: int = 30, seed: int | None = None):
        self.num_reps = max(num_reps, 30)  # D4 requires >= 30 reps.
        self.seed = seed

    def _collect(self, scenario: str) -> tuple[list[float], list[int]]:
        params = SCENARIO_PARAMS[scenario]
        times: list[float] = []
        retx: list[int] = []
        for _ in range(self.num_reps):
            protocol = GBNProtocol(
                window_size=8,
                timeout_ms=500,
                mean_delay_ms=params["mean_delay_ms"],
                loss_rate=params["loss_rate"],
            )
            protocol.transfer(b"X" * PAYLOAD_BYTES)
            times.append(protocol.elapsed_s)
            retx.append(protocol.retrans_count)
        return times, retx

    def analyze_scenario(self, scenario: str) -> dict:
        times, retx = self._collect(scenario)
        t_mean, t_lo, t_hi = bootstrap_ci(times, seed=self.seed)
        r_mean, r_lo, r_hi = bootstrap_ci(
            [float(x) for x in retx], seed=self.seed
        )
        return {
            "scenario": scenario,
            "n": len(times),
            "time_mean_s": t_mean,
            "time_std_s": float(np.std(times, ddof=1)),
            "time_ci_lower": t_lo,
            "time_ci_upper": t_hi,
            "retx_mean": r_mean,
            "retx_std": float(np.std(retx, ddof=1)),
            "retx_ci_lower": r_lo,
            "retx_ci_upper": r_hi,
        }

    def generate_report(self) -> str:
        report = "\n=== Convergence (>=30 reps, bootstrap 95% CI) ===\n"
        report += (
            "Scn | n  | Time mean (s) | 95% CI            "
            "| Real (s) | covers?\n"
        )
        report += (
            "----|----|---------------|-------------------"
            "|----------|--------\n"
        )
        for scenario in ["A", "B", "C"]:
            r = self.analyze_scenario(scenario)
            real = REAL_DATA[scenario]["time_mean_s"]
            covers = r["time_ci_lower"] <= real <= r["time_ci_upper"]
            report += (
                f"{scenario:3} | {r['n']:2d} | "
                f"{r['time_mean_s']:13.3f} | "
                f"[{r['time_ci_lower']:7.3f}, {r['time_ci_upper']:7.3f}] | "
                f"{real:8.3f} | {'yes' if covers else 'NO':>6}\n"
            )
        return report


if __name__ == "__main__":
    print(ConvergenceAnalyzer(num_reps=30).generate_report())
