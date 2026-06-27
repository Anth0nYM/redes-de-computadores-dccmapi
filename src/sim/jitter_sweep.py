"""Jitter-impact study (D7, task 7: mais jitter -> mais variancia).

The per-packet propagation delay is Normal(mean, jitter); the jitter is its
standard deviation. With more jitter each round-trip sample spreads wider, so
the accumulated transfer time over the whole transfer spreads wider too. This
module sweeps the jitter on an otherwise clean channel (scenario A, no loss,
so the variance is purely jitter-driven) and reports, for each jitter, the
mean and the run-to-run standard deviation of the transfer time. The FIFO
link still preserves packet order, so the variance comes from delay spread,
not from spurious reordering timeouts.
"""

import os
import random

import numpy as np

from src.sim.gbn import GBNProtocol
from src.sim.validate import BLOCK_SIZE

ONE_MB = 1024 * 1024
# Jitter as an absolute std in ms; the default spans <1 RTT to a full RTT.
DEFAULT_JITTERS = [1, 5, 10, 20, 40, 80]


def measure_time_stats(
    jitter_ms: float,
    mean_delay_ms: float = 50,
    loss_rate: float = 0.0,
    size_mb: float = 0.25,
    reps: int = 40,
    seed: int | None = None,
) -> tuple[float, float]:
    """Mean and sample-std (ddof=1) of the transfer time (s) over ``reps``.

    A clean channel by default, so the spread isolates the jitter effect.
    The shared RNG is seeded once so a given (jitter, seed) is reproducible.
    """
    if seed is not None:
        random.seed(seed)

    payload = int(size_mb * ONE_MB)
    times = []
    for _ in range(reps):
        protocol = GBNProtocol(
            window_size=8,
            timeout_ms=500,
            mean_delay_ms=mean_delay_ms,
            loss_rate=loss_rate,
            jitter_ms=jitter_ms,
        )
        protocol.transfer(b"X" * payload, block_size=BLOCK_SIZE)
        times.append(protocol.elapsed_s)

    arr = np.asarray(times, dtype=float)
    std = float(arr.std(ddof=1)) if len(arr) > 1 else 0.0
    return float(arr.mean()), std


class JitterSweep:
    """Sweeps the jitter to show the transfer-time variance growing with it."""

    def __init__(
        self,
        jitters: list[float] | None = None,
        mean_delay_ms: float = 50,
        loss_rate: float = 0.0,
        size_mb: float = 0.25,
        reps: int = 40,
        seed: int | None = None,
    ):
        self.jitters = jitters if jitters is not None else list(DEFAULT_JITTERS)
        self.mean_delay_ms = mean_delay_ms
        self.loss_rate = loss_rate
        self.size_mb = size_mb
        self.reps = reps
        self.seed = seed
        self._result: tuple[list[float], list[float], list[float]] | None = None

    def compute(self) -> tuple[list[float], list[float], list[float]]:
        """Return (jitters, mean_times_s, std_times_s), caching the result."""
        if self._result is None:
            means: list[float] = []
            stds: list[float] = []
            for j in self.jitters:
                mean, std = measure_time_stats(
                    jitter_ms=j,
                    mean_delay_ms=self.mean_delay_ms,
                    loss_rate=self.loss_rate,
                    size_mb=self.size_mb,
                    reps=self.reps,
                    seed=self.seed,
                )
                means.append(mean)
                stds.append(std)
            self._result = (list(self.jitters), means, stds)
        return self._result

    def variance_increases(self) -> bool:
        """True if the std of the transfer time grows monotonically with jitter."""
        _, _, stds = self.compute()
        return all(b > a for a, b in zip(stds, stds[1:]))


def generate_figure(
    output_path: str = "results/figures/fig_jitter.png",
    jitters: list[float] | None = None,
    reps: int = 40,
    seed: int | None = 1,
) -> str:
    """Render mean transfer time with +/-1 std error bars vs jitter."""
    import plotly.graph_objects as go

    sweep = JitterSweep(jitters=jitters, reps=reps, seed=seed)
    jit, means, stds = sweep.compute()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=jit,
            y=means,
            mode="lines+markers",
            name="Tempo medio +/- 1 desvio",
            line=dict(color="#1f77b4"),
            error_y=dict(type="data", array=stds, visible=True),
        )
    )
    fig.update_layout(
        title=(
            f"Impacto do jitter na variancia do tempo "
            f"(canal limpo, RTT {2 * sweep.mean_delay_ms:.0f} ms)"
        ),
        xaxis_title="Jitter (desvio do atraso, ms)",
        yaxis_title="Tempo de transferencia (s)",
        template="plotly_white",
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.write_image(output_path)
    return output_path


if __name__ == "__main__":
    sweep = JitterSweep(seed=1)
    jit, means, stds = sweep.compute()
    print("Impacto do jitter (canal limpo, cenario A):")
    print(" jitter(ms) | tempo medio(s) | desvio(s)")
    print(" -----------|----------------|----------")
    for j, m, s in zip(jit, means, stds):
        print(f" {j:10.0f} | {m:14.4f} | {s:8.5f}")
    print(
        f"\nVariancia cresce monotonicamente com o jitter? "
        f"{'sim' if sweep.variance_increases() else 'NAO'}"
    )
