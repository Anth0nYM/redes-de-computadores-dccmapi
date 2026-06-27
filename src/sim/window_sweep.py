"""Window-sensitivity curve (D6, task 5: saturação teórica ao variar N).

With a finite bottleneck bandwidth the pipe holds BDP = bandwidth x RTT bytes,
i.e. ``BDP / block`` packets. Below that window the protocol is window-limited
and throughput grows linearly with N; above it the link is the bottleneck and
extra window buys nothing. The curve therefore has a knee at ``N* = BDP/block``.
The real loopback link had no tight rate limit (it was window-limited), so this
study injects an explicit bottleneck to expose the theoretical saturation.
"""

import os

from src.sim.gbn import GBNProtocol
from src.sim.validate import SCENARIO_PARAMS, BLOCK_SIZE

ONE_MB = 1024 * 1024
DEFAULT_WINDOWS = [1, 2, 4, 6, 8, 10, 12, 16, 20, 24, 28, 32]


def theoretical_knee_N(bandwidth_KBps: float, rtt_s: float, block_size: int) -> float:
    """Window that just fills the pipe: N* = BDP / block = bw * RTT / block."""
    bdp_bytes = bandwidth_KBps * 1024 * rtt_s
    return bdp_bytes / block_size


def _rtt_s(scenario: str) -> float:
    return 2 * SCENARIO_PARAMS[scenario]["mean_delay_ms"] / 1000.0


def measure_throughput_for_window(
    window: int,
    bandwidth_KBps: float,
    scenario: str = "A",
    size_mb: float = 5,
    reps: int = 5,
) -> float:
    """Mean throughput (KB/s) for a given window size over a clean bottleneck."""
    params = SCENARIO_PARAMS[scenario]
    payload = int(size_mb * ONE_MB)
    size_kb = payload / 1024

    tputs = []
    for _ in range(reps):
        protocol = GBNProtocol(
            window_size=window,
            timeout_ms=500,
            mean_delay_ms=params["mean_delay_ms"],
            loss_rate=params["loss_rate"],
            bandwidth_KBps=bandwidth_KBps,
        )
        protocol.transfer(b"X" * payload, block_size=BLOCK_SIZE)
        tputs.append(size_kb / protocol.elapsed_s)

    return sum(tputs) / len(tputs)


class WindowSweep:
    """Sweeps the window size N over a clean bottleneck link to find the knee."""

    def __init__(
        self,
        bandwidth_KBps: float,
        windows: list[int] | None = None,
        scenario: str = "A",
        size_mb: float = 5,
        reps: int = 5,
    ):
        self.bandwidth_KBps = bandwidth_KBps
        self.windows = windows if windows is not None else list(DEFAULT_WINDOWS)
        self.scenario = scenario
        self.size_mb = size_mb
        self.reps = reps
        self._tputs: list[float] | None = None

    def compute(self) -> tuple[list[int], list[float]]:
        """Return (windows, throughputs_KBps), caching the result."""
        if self._tputs is None:
            self._tputs = [
                measure_throughput_for_window(
                    window=w,
                    bandwidth_KBps=self.bandwidth_KBps,
                    scenario=self.scenario,
                    size_mb=self.size_mb,
                    reps=self.reps,
                )
                for w in self.windows
            ]
        return self.windows, self._tputs

    def knee_N(self) -> float:
        """Theoretical knee BDP/block for this study's bottleneck."""
        return theoretical_knee_N(
            self.bandwidth_KBps, _rtt_s(self.scenario), BLOCK_SIZE
        )

    def measured_knee_N(self) -> int:
        """Smallest window reaching 95% of the saturated (max) throughput."""
        windows, tputs = self.compute()
        threshold = 0.95 * max(tputs)
        for w, t in zip(windows, tputs):
            if t >= threshold:
                return w
        return windows[-1]


def build_figure(
    bandwidth_KBps: float = 2000.0,
    windows: list[int] | None = None,
    reps: int = 5,
):
    """Build and return the throughput-vs-window figure with the knee marked."""
    import plotly.graph_objects as go

    sweep = WindowSweep(bandwidth_KBps=bandwidth_KBps, windows=windows, reps=reps)
    win, tputs = sweep.compute()
    knee = sweep.knee_N()

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=win, y=tputs, mode="lines+markers",
            name="Vazão (sim)", line=dict(color="#1f77b4"),
        )
    )
    fig.add_hline(
        y=bandwidth_KBps, line_dash="dash", line_color="#7f7f7f",
        annotation_text=f"banda do link: {bandwidth_KBps:.0f} KB/s",
        annotation_position="bottom right",
    )
    fig.add_vline(
        x=knee, line_dash="dot", line_color="#d62728",
        annotation_text=f"joelho N*=BDP/bloco={knee:.0f}",
        annotation_position="top left",
    )
    fig.update_layout(
        title="Sensibilidade da janela N (cenário A, link 2000 KB/s)",
        xaxis_title="Tamanho da janela N (pacotes)",
        yaxis_title="Vazão (KB/s)",
        template="plotly_white",
    )
    return fig


def generate_figure(
    output_path: str = "results/figures/fig_janela.png",
    bandwidth_KBps: float = 2000.0,
    windows: list[int] | None = None,
    reps: int = 5,
) -> str:
    """Render the throughput-vs-window figure to a PNG and return its path."""
    fig = build_figure(
        bandwidth_KBps=bandwidth_KBps, windows=windows, reps=reps
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.write_image(output_path)
    return output_path


if __name__ == "__main__":
    sweep = WindowSweep(bandwidth_KBps=2000.0)
    win, tputs = sweep.compute()
    print(
        f"Joelho teórico N* = {sweep.knee_N():.1f} ; "
        f"joelho medido = {sweep.measured_knee_N()}"
    )
    for w, t in zip(win, tputs):
        print(f"  N={w:2d} -> {t:8.1f} KB/s")
