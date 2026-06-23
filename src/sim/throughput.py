"""Throughput-vs-filesize curve (D5, task 4: vazão de 1 MB a 100 MB).

A window-limited protocol caps throughput at ``window * block / RTT`` (the
sender keeps at most ``window`` packets in flight per RTT). For small files the
fixed connection-setup RTT is a large fraction of the transfer, so throughput
sits below the ceiling; as the file grows the setup amortizes and throughput
saturates at the ceiling. This module measures that curve from the SimPy engine
and renders it to ``fig_vazao_tamanho.png``.
"""

import os

from src.sim.gbn import GBNProtocol
from src.sim.validate import SCENARIO_PARAMS, BLOCK_SIZE

ONE_MB = 1024 * 1024
DEFAULT_SIZES_MB = [1, 2, 5, 10, 25, 50, 100]


def theoretical_throughput_KBps(window: int, block_size: int, rtt_s: float) -> float:
    """Window-limited throughput ceiling, in KB/s."""
    return window * block_size / rtt_s / 1024


def _rtt_s(scenario: str) -> float:
    """Round-trip time for a scenario (2x the one-way mean delay)."""
    return 2 * SCENARIO_PARAMS[scenario]["mean_delay_ms"] / 1000.0


def measure_throughput_KBps(
    size_mb: float,
    scenario: str = "A",
    reps: int = 5,
    window_size: int = 8,
    timeout_ms: float = 500,
) -> float:
    """Mean throughput (KB/s) for a file of ``size_mb`` over ``scenario``."""
    params = SCENARIO_PARAMS[scenario]
    payload = int(size_mb * ONE_MB)
    size_kb = payload / 1024

    tputs = []
    for _ in range(reps):
        protocol = GBNProtocol(
            window_size=window_size,
            timeout_ms=timeout_ms,
            mean_delay_ms=params["mean_delay_ms"],
            loss_rate=params["loss_rate"],
        )
        protocol.transfer(b"X" * payload, block_size=BLOCK_SIZE)
        tputs.append(size_kb / protocol.elapsed_s)

    return sum(tputs) / len(tputs)


class ThroughputCurve:
    """Sweeps file sizes for one scenario to build the throughput curve."""

    def __init__(
        self,
        scenario: str = "A",
        sizes_mb: list[float] | None = None,
        reps: int = 5,
        window_size: int = 8,
    ):
        self.scenario = scenario
        self.sizes_mb = sizes_mb if sizes_mb is not None else list(DEFAULT_SIZES_MB)
        self.reps = reps
        self.window_size = window_size

    def compute(self) -> tuple[list[float], list[float]]:
        """Return (sizes_mb, throughputs_KBps)."""
        tputs = [
            measure_throughput_KBps(
                size_mb=size,
                scenario=self.scenario,
                reps=self.reps,
                window_size=self.window_size,
            )
            for size in self.sizes_mb
        ]
        return self.sizes_mb, tputs

    def ceiling_KBps(self) -> float:
        return theoretical_throughput_KBps(
            self.window_size, BLOCK_SIZE, _rtt_s(self.scenario)
        )


def generate_figure(
    output_path: str = "results/figures/fig_vazao_tamanho.png",
    scenarios: list[str] | None = None,
    sizes_mb: list[float] | None = None,
    reps: int = 5,
) -> str:
    """Render the throughput-vs-filesize figure with Plotly."""
    import plotly.graph_objects as go

    scenarios = scenarios or ["A", "B"]
    sizes_mb = sizes_mb if sizes_mb is not None else list(DEFAULT_SIZES_MB)

    fig = go.Figure()
    colors = {"A": "#2ca02c", "B": "#ff7f0e", "C": "#d62728"}

    for scenario in scenarios:
        curve = ThroughputCurve(scenario=scenario, sizes_mb=sizes_mb, reps=reps)
        sizes, tputs = curve.compute()
        fig.add_trace(
            go.Scatter(
                x=sizes,
                y=tputs,
                mode="lines+markers",
                name=f"Cenário {scenario} (sim)",
                line=dict(color=colors.get(scenario)),
            )
        )
        ceiling = curve.ceiling_KBps()
        fig.add_hline(
            y=ceiling,
            line_dash="dash",
            line_color=colors.get(scenario),
            annotation_text=f"teto {scenario}: {ceiling:.0f} KB/s",
            annotation_position="top right",
        )

    fig.update_layout(
        title="Vazão vs. tamanho do arquivo (GBN, janela=8)",
        xaxis_title="Tamanho do arquivo (MB)",
        yaxis_title="Vazão (KB/s)",
        template="plotly_white",
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.write_image(output_path)
    return output_path


if __name__ == "__main__":
    for scn in ["A", "B"]:
        curve = ThroughputCurve(scenario=scn)
        sizes, tputs = curve.compute()
        ceiling = curve.ceiling_KBps()
        print(f"\nCenário {scn} (teto teórico {ceiling:.0f} KB/s):")
        for size, tput in zip(sizes, tputs):
            print(f"  {size:6.1f} MB -> {tput:8.1f} KB/s ({100*tput/ceiling:.1f}% do teto)")
