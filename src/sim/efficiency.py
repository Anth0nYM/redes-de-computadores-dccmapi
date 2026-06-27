"""Efficiency study (D9, task 9: razao entre pacotes de DADOS e de ACK).

A Go-Back-N receiver answers every arriving DATA packet with one cumulative
ACK, so the only DATA packets that go unACKed are the ones the channel drops,
and the lost ones are re-sent. The DATA/ACK ratio is therefore ~1 on a clean
link and climbs as ``1/(1-p_eff)`` with loss: each successful ACK costs ever
more DATA transmissions, i.e. the protocol grows less efficient. This module
counts DATA and ACK packets (instrumented in the engine) per scenario and
reports the ratio, which worsens monotonically from A to C.
"""

import os
import random

import numpy as np

from src.sim.gbn import GBNProtocol
from src.sim.validate import SCENARIO_PARAMS, PAYLOAD_BYTES, BLOCK_SIZE


def measure_efficiency(
    scenario: str,
    reps: int = 30,
    seed: int | None = None,
) -> dict:
    """Mean DATA/ACK packet counts and their ratio for a scenario over reps."""
    if seed is not None:
        random.seed(seed)

    params = SCENARIO_PARAMS[scenario]
    data_counts: list[int] = []
    ack_counts: list[int] = []
    for _ in range(reps):
        protocol = GBNProtocol(
            window_size=8,
            timeout_ms=500,
            mean_delay_ms=params["mean_delay_ms"],
            loss_rate=params["loss_rate"],
        )
        protocol.transfer(b"X" * PAYLOAD_BYTES, block_size=BLOCK_SIZE)
        data_counts.append(protocol.data_packets)
        ack_counts.append(protocol.ack_packets)

    data_mean = float(np.mean(data_counts))
    ack_mean = float(np.mean(ack_counts))
    return {
        "scenario": scenario,
        "loss_rate": params["loss_rate"],
        "data_mean": data_mean,
        "ack_mean": ack_mean,
        "ratio": data_mean / ack_mean,
    }


class EfficiencyStudy:
    """Compares the DATA/ACK ratio across scenarios A, B and C."""

    def __init__(
        self,
        scenarios: list[str] | None = None,
        reps: int = 30,
        seed: int | None = None,
    ):
        self.scenarios = scenarios if scenarios is not None else ["A", "B", "C"]
        self.reps = reps
        self.seed = seed
        self._rows: dict | None = None

    def compute(self) -> dict:
        """Return {scenario: efficiency-dict}, caching the result."""
        if self._rows is None:
            self._rows = {
                s: measure_efficiency(s, self.reps, self.seed)
                for s in self.scenarios
            }
        return self._rows

    def generate_report(self) -> str:
        rows = self.compute()
        out = "\n=== Eficiencia DATA/ACK (D9) ===\n"
        out += "Cen | perda  | DATA   | ACK    | razao DATA/ACK | 1/(1-p)\n"
        out += "----|--------|--------|--------|----------------|--------\n"
        for s in self.scenarios:
            r = rows[s]
            inv = 1.0 / (1.0 - r["loss_rate"])
            out += (
                f"{s:3} | {r['loss_rate']:.3f}  | {r['data_mean']:6.0f} | "
                f"{r['ack_mean']:6.0f} | {r['ratio']:14.3f} | {inv:6.3f}\n"
            )
        out += "\nRazao ~1 = eficiente (1 ACK por DATA); cresce com a perda.\n"
        return out


def build_figure(
    reps: int = 30,
    seed: int | None = 1,
):
    """Build the DATA/ACK ratio bar chart per scenario."""
    import plotly.graph_objects as go

    study = EfficiencyStudy(reps=reps, seed=seed)
    rows = study.compute()
    scenarios = study.scenarios
    ratios = [rows[s]["ratio"] for s in scenarios]
    labels = [
        f"{s}<br>perda {rows[s]['loss_rate']:.1%}" for s in scenarios
    ]

    fig = go.Figure(
        go.Bar(
            x=labels,
            y=ratios,
            text=[f"{r:.2f}" for r in ratios],
            textposition="outside",
            marker_color=["#2ca02c", "#ff7f0e", "#d62728"],
        )
    )
    fig.add_hline(
        y=1.0, line_dash="dash", line_color="#7f7f7f",
        annotation_text="ideal = 1 ACK por DATA",
        annotation_position="top left",
    )
    fig.update_layout(
        title="Eficiencia: razao de pacotes DATA/ACK por cenario",
        xaxis_title="Cenario",
        yaxis_title="Razao DATA/ACK (maior = pior)",
        template="plotly_white",
    )
    return fig


def generate_figure(
    output_path: str = "results/figures/fase2_eficiencia.png",
    reps: int = 30,
    seed: int | None = 1,
) -> str:
    """Render the efficiency figure to a PNG and return its path."""
    fig = build_figure(reps=reps, seed=seed)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.write_image(output_path)
    return output_path


if __name__ == "__main__":
    print(EfficiencyStudy(reps=30, seed=1).generate_report())
