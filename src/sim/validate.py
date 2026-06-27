"""Calibration validation against real network data.

Each scenario runs the GBN simulator and reports the simulated transfer
time and retransmission count, both emergent from the channel model (no
hardcoded multipliers). The anchors come from results/tables/summary_stats.csv
and the paper: RTT ~20/100/200 ms, effective loss 1-(1-p)^3.
"""

from src.sim.gbn import GBNProtocol

# Real RUDP measurements (results/tables/summary_stats.csv).
REAL_DATA = {
    "A": {"time_mean_s": 0.676, "retx_mean": 0.0},
    "B": {"time_mean_s": 53.165, "retx_mean": 91.1},
    "C": {"time_mean_s": 144.613, "retx_mean": 238.5},
}

# Per-scenario channel parameters (anchored to the paper).
SCENARIO_PARAMS = {
    "A": {"mean_delay_ms": 10, "loss_rate": 0.0},
    "B": {"mean_delay_ms": 50, "loss_rate": 0.271},
    "C": {"mean_delay_ms": 100, "loss_rate": 0.488},
}

# Real R-UDP used 4 KiB blocks: 256 blocks == a 1 MiB file (matches the real
# tput_mean of ~1515 KBps for scenario A). Block size drives throughput; the
# RTT-bound time model depends on the block count (256), not the block size.
BLOCK_SIZE = 4096
PAYLOAD_BYTES = 256 * BLOCK_SIZE  # 1 MiB, 256 blocks


class CalibrationValidator:
    """Validates simulator calibration against real data."""

    def __init__(self, num_reps: int = 30):
        self.num_reps = num_reps

    def _run_scenario(self, scenario: str) -> dict:
        params = SCENARIO_PARAMS[scenario]
        times = []
        retx_list = []

        for _ in range(self.num_reps):
            protocol = GBNProtocol(
                window_size=8,
                timeout_ms=500,
                mean_delay_ms=params["mean_delay_ms"],
                loss_rate=params["loss_rate"],
            )
            protocol.transfer(b"X" * PAYLOAD_BYTES, block_size=BLOCK_SIZE)
            times.append(protocol.elapsed_s)
            retx_list.append(protocol.retrans_count)

        return {
            "time_mean_s": sum(times) / len(times),
            "retx_mean": sum(retx_list) / len(retx_list),
        }

    def run_scenario_a(self) -> dict:
        """Scenario A: no loss, low latency."""
        return self._run_scenario("A")

    def run_scenario_b(self) -> dict:
        """Scenario B: medium loss (~27.1% effective)."""
        return self._run_scenario("B")

    def run_scenario_c(self) -> dict:
        """Scenario C: high loss (~48.8% effective)."""
        return self._run_scenario("C")

    def generate_report(self) -> str:
        """Generate comparison table: simulation vs real data."""
        report = "\n=== Calibration Report (sim vs real) ===\n"
        report += "Scenario | Sim Time (s) | Real Time (s) | Sim Retx | Real Retx\n"
        report += "---------|--------------|---------------|----------|----------\n"

        for scenario in ["A", "B", "C"]:
            sim = self._run_scenario(scenario)
            real = REAL_DATA[scenario]
            report += (
                f"{scenario:8} | "
                f"{sim['time_mean_s']:12.3f} | "
                f"{real['time_mean_s']:13.3f} | "
                f"{sim['retx_mean']:8.1f} | "
                f"{real['retx_mean']:8.1f}\n"
            )

        return report


def _sim_vs_real(num_reps: int = 30) -> dict:
    """Collect sim and real (time, retx) per scenario for the calibration plots."""
    validator = CalibrationValidator(num_reps=num_reps)
    rows = {s: validator._run_scenario(s) for s in ("A", "B", "C")}
    return rows


def build_time_figure(num_reps: int = 30):
    """Grouped bars comparing simulated vs real transfer time per scenario."""
    import plotly.graph_objects as go

    scenarios = ["A", "B", "C"]
    rows = _sim_vs_real(num_reps)
    sim = [rows[s]["time_mean_s"] for s in scenarios]
    real = [REAL_DATA[s]["time_mean_s"] for s in scenarios]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=scenarios, y=sim, name="Simulado", marker_color="#1f77b4"))
    fig.add_trace(go.Bar(x=scenarios, y=real, name="Real", marker_color="#d62728"))
    fig.update_layout(
        title="Calibração: tempo de transferência (sim vs real)",
        xaxis_title="Cenário",
        yaxis_title="Tempo (s)",
        barmode="group",
        template="plotly_white",
    )
    return fig


def build_retx_figure(num_reps: int = 30):
    """Grouped bars comparing simulated vs real retransmissions per scenario."""
    import plotly.graph_objects as go

    scenarios = ["A", "B", "C"]
    rows = _sim_vs_real(num_reps)
    sim = [rows[s]["retx_mean"] for s in scenarios]
    real = [REAL_DATA[s]["retx_mean"] for s in scenarios]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=scenarios, y=sim, name="Simulado", marker_color="#1f77b4"))
    fig.add_trace(go.Bar(x=scenarios, y=real, name="Real", marker_color="#d62728"))
    fig.update_layout(
        title="Calibração: retransmissões (sim vs real)",
        xaxis_title="Cenário",
        yaxis_title="Retransmissões (eventos de timeout)",
        barmode="group",
        template="plotly_white",
    )
    return fig


if __name__ == "__main__":
    print(CalibrationValidator().generate_report())
