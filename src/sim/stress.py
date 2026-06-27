"""Stress-scenario forecast (D8, task 8: prever o tempo com 25% de perda).

The tc loss configured per scenario is the *raw* per-packet drop (A 0%, B 10%,
C 20%). A 4112 B R-UDP datagram spans 3 IP fragments, so a block is lost when
any fragment is lost: the *effective* per-block loss the simulator consumes is
``p_eff = 1-(1-p)^3`` (this is how B->27.1% and C->48.8% were calibrated).

Task 8 forecasts the transfer time at a 25% raw-loss stress. Keeping C's
latency (100 ms) isolates the extra loss, so the prediction is read directly
against the C anchor: at 20% raw the model reproduces real C, and 25% raw
(p_eff ~57.8%) lands above C on the monotone loss->time curve.
"""

import os
import random

import numpy as np

from src.sim.gbn import GBNProtocol
from src.sim.converge import bootstrap_ci
from src.sim.validate import REAL_DATA, PAYLOAD_BYTES, BLOCK_SIZE

# Raw tc loss for the stress test, and the latency held fixed at C's value so
# the forecast isolates the loss increase rather than mixing in a delay change.
STRESS_RAW_LOSS = 0.25
C_RAW_LOSS = 0.20
STRESS_DELAY_MS = 100
IP_FRAGMENTS = 3


def effective_loss(raw_loss: float, fragments: int = IP_FRAGMENTS) -> float:
    """Effective per-block loss when each block spans ``fragments`` IP packets."""
    return 1.0 - (1.0 - raw_loss) ** fragments


def forecast_time(
    raw_loss: float = STRESS_RAW_LOSS,
    mean_delay_ms: float = STRESS_DELAY_MS,
    reps: int = 30,
    seed: int | None = None,
) -> dict:
    """Forecast the transfer time at a given raw loss over >=30 reps.

    Returns a dict with the raw/effective loss, the mean and sample-std of the
    transfer time, a bootstrap 95% CI on the mean, and the rep count.
    """
    if seed is not None:
        random.seed(seed)

    reps = max(reps, 30)  # task 10 convention: >= 30 reps for the estimate.
    p_eff = effective_loss(raw_loss)

    times: list[float] = []
    for _ in range(reps):
        protocol = GBNProtocol(
            window_size=8,
            timeout_ms=500,
            mean_delay_ms=mean_delay_ms,
            loss_rate=p_eff,
        )
        protocol.transfer(b"X" * PAYLOAD_BYTES, block_size=BLOCK_SIZE)
        times.append(protocol.elapsed_s)

    mean, ci_lo, ci_hi = bootstrap_ci(times, seed=seed)
    return {
        "raw_loss": raw_loss,
        "p_eff": p_eff,
        "mean": mean,
        "std": float(np.std(times, ddof=1)),
        "ci_lo": ci_lo,
        "ci_hi": ci_hi,
        "n": len(times),
    }


class StressForecast:
    """Forecasts the 25% stress time and pins it against the C anchor."""

    def __init__(
        self,
        mean_delay_ms: float = STRESS_DELAY_MS,
        reps: int = 30,
        seed: int | None = None,
    ):
        self.mean_delay_ms = mean_delay_ms
        self.reps = reps
        self.seed = seed
        self._report: dict | None = None

    def forecast(self) -> dict:
        """Return {'c_anchor': ..., 'stress': ...} forecasts, caching them."""
        if self._report is None:
            self._report = {
                "c_anchor": forecast_time(
                    C_RAW_LOSS, self.mean_delay_ms, self.reps, self.seed
                ),
                "stress": forecast_time(
                    STRESS_RAW_LOSS, self.mean_delay_ms, self.reps, self.seed
                ),
            }
        return self._report

    def generate_report(self) -> str:
        r = self.forecast()
        real_c = REAL_DATA["C"]["time_mean_s"]
        c, s = r["c_anchor"], r["stress"]
        out = "\n=== Cenario de estresse (previsao de tempo, D8) ===\n"
        out += "Caso       | perda bruta | p_eff  | tempo medio(s) | 95% CI\n"
        out += "-----------|-------------|--------|----------------|------------------\n"
        out += (
            f"C (ancora) | {c['raw_loss']:10.0%} | {c['p_eff']:.3f} | "
            f"{c['mean']:14.2f} | [{c['ci_lo']:.2f}, {c['ci_hi']:.2f}]\n"
        )
        out += (
            f"Estresse   | {s['raw_loss']:10.0%} | {s['p_eff']:.3f} | "
            f"{s['mean']:14.2f} | [{s['ci_lo']:.2f}, {s['ci_hi']:.2f}]\n"
        )
        out += f"\nReal C medido: {real_c:.2f} s "
        out += f"(sim ancora {c['mean']:.2f} s, erro {abs(c['mean']-real_c)/real_c:.1%}).\n"
        out += (
            f"Previsao 25%: {s['mean']:.2f} s, "
            f"{'acima' if s['mean'] > real_c else 'ABAIXO'} de C "
            f"(+{(s['mean']/real_c - 1):.0%}) -> coerente.\n"
        )
        return out


def build_figure(
    reps: int = 30,
    seed: int | None = 1,
):
    """Build the forecast-vs-loss curve with the real C anchor marked."""
    import plotly.graph_objects as go

    raws = [0.10, 0.20, 0.25]
    points = [forecast_time(r, STRESS_DELAY_MS, reps, seed) for r in raws]
    means = [p["mean"] for p in points]
    stds = [p["std"] for p in points]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[r * 100 for r in raws],
            y=means,
            mode="lines+markers",
            name="Previsao (sim, atraso 100 ms)",
            line=dict(color="#1f77b4"),
            error_y=dict(type="data", array=stds, visible=True),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[20],
            y=[REAL_DATA["C"]["time_mean_s"]],
            mode="markers",
            name="Real C (medido)",
            marker=dict(color="#d62728", size=12, symbol="x"),
        )
    )
    fig.add_vline(
        x=25, line_dash="dot", line_color="#7f7f7f",
        annotation_text="estresse 25%", annotation_position="top left",
    )
    fig.update_layout(
        title="Cenario de estresse: previsao de tempo vs perda de pacotes",
        xaxis_title="Perda bruta de pacotes (%)",
        yaxis_title="Tempo de transferencia (s)",
        template="plotly_white",
    )
    return fig


def generate_figure(
    output_path: str = "results/figures/fig_estresse.png",
    reps: int = 30,
    seed: int | None = 1,
) -> str:
    """Render the stress forecast figure to a PNG and return its path."""
    fig = build_figure(reps=reps, seed=seed)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.write_image(output_path)
    return output_path


if __name__ == "__main__":
    print(StressForecast(reps=30, seed=1).generate_report())
