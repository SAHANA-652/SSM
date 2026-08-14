"""
Matplotlib visualizations for comparing drive-through configurations.

All figures are saved to disk for lab reports; ``plt.show()`` is optional in ``main``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from metrics import ScenarioResult


def _ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def plot_waiting_time_vs_servers(
    results: Sequence[ScenarioResult],
    output_path: Optional[Path] = None,
    arrival_mode: str = "normal",
) -> Figure:
    """Average waiting time as a function of parallel windows."""
    subset = [r for r in results if r.arrival_mode == arrival_mode]
    subset = sorted(subset, key=lambda r: r.num_servers)
    servers = [r.num_servers for r in subset]
    waits = [r.average_waiting_time for r in subset]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(servers, waits, marker="o", linewidth=2, label=f"{arrival_mode.title()} traffic")
    ax.set_xlabel("Number of service windows")
    ax.set_ylabel("Average waiting time (minutes)")
    ax.set_title("Waiting Time vs Number of Servers")
    ax.set_xticks(servers)
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.legend()
    fig.tight_layout()
    if output_path is not None:
        _ensure_output_dir(output_path.parent)
        fig.savefig(output_path, dpi=160)
    return fig


def plot_queue_length_timeseries(
    series: Dict[str, Sequence[Tuple[float, int]]],
    output_path: Optional[Path] = None,
    horizon_minutes: float = 480.0,
) -> Figure:
    """Piecewise-constant queue length curves for selected scenarios."""
    fig, ax = plt.subplots(figsize=(9, 5))
    for label, points in series.items():
        if not points:
            continue
        times = np.array([p[0] for p in points], dtype=float)
        lengths = np.array([p[1] for p in points], dtype=int)
        ax.step(times, lengths, where="post", label=label, linewidth=1.8)
    ax.set_xlim(0.0, max(horizon_minutes, 1.0))
    ax.set_xlabel("Simulation time (minutes)")
    ax.set_ylabel("Customers waiting (FIFO lane)")
    ax.set_title("Queue Length Dynamics")
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.legend()
    fig.tight_layout()
    if output_path is not None:
        _ensure_output_dir(output_path.parent)
        fig.savefig(output_path, dpi=160)
    return fig


def plot_lost_customers_bar(results: Sequence[ScenarioResult], output_path: Optional[Path] = None) -> Figure:
    """Bar chart of lost customers due to excessive waiting."""
    labels = [r.scenario_name for r in results]
    lost = [r.lost_customers for r in results]

    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(labels))
    ax.bar(x, lost, color="#c0392b", alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.set_ylabel("Lost customers (reneged)")
    ax.set_title("Lost Customers by Scenario")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    fig.tight_layout()
    if output_path is not None:
        _ensure_output_dir(output_path.parent)
        fig.savefig(output_path, dpi=160)
    return fig


def plot_throughput_comparison(results: Sequence[ScenarioResult], output_path: Optional[Path] = None) -> Figure:
    """Completed customers per hour across scenarios."""
    labels = [r.scenario_name for r in results]
    thr = [r.throughput_per_hour for r in results]

    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(labels))
    ax.bar(x, thr, color="#2980b9", alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.set_ylabel("Throughput (customers / hour)")
    ax.set_title("Throughput Comparison")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    fig.tight_layout()
    if output_path is not None:
        _ensure_output_dir(output_path.parent)
        fig.savefig(output_path, dpi=160)
    return fig


def plot_peak_hour_analysis(
    normal_results: Sequence[ScenarioResult],
    peak_results: Sequence[ScenarioResult],
    output_path: Optional[Path] = None,
) -> Figure:
    """
    Grouped metrics for the same server counts under normal vs peak arrival rates.

    Expect both sequences sorted by ``num_servers`` with matching lengths.
    """
    if len(normal_results) != len(peak_results):
        raise ValueError("normal and peak result sets must align for paired plotting.")

    servers = [r.num_servers for r in normal_results]
    x = np.arange(len(servers))
    width = 0.35

    waits_n = [r.average_waiting_time for r in normal_results]
    waits_p = [r.average_waiting_time for r in peak_results]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(x - width / 2, waits_n, width, label="Normal arrival rate", color="#16a085")
    ax.bar(x + width / 2, waits_p, width, label="Peak arrival rate", color="#e67e22")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{s} window(s)" for s in servers])
    ax.set_ylabel("Average waiting time (minutes)")
    ax.set_title("Peak Hour Analysis: Waiting Time")
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    fig.tight_layout()
    if output_path is not None:
        _ensure_output_dir(output_path.parent)
        fig.savefig(output_path, dpi=160)
    return fig


def generate_all_figures(
    results: List[ScenarioResult],
    queue_series: Dict[str, Sequence[Tuple[float, int]]],
    horizon_minutes: float,
    output_dir: Path,
    show: bool = False,
) -> None:
    """Create the five required figures in one call."""
    output_dir = Path(output_dir)
    _ensure_output_dir(output_dir)

    plt.close("all")

    plot_waiting_time_vs_servers(results, output_dir / "fig1_waiting_vs_servers.png")
    plot_queue_length_timeseries(queue_series, output_dir / "fig2_queue_length.png", horizon_minutes)
    plot_lost_customers_bar(results, output_dir / "fig3_lost_customers.png")
    plot_throughput_comparison(results, output_dir / "fig4_throughput.png")

    normal_pair = sorted([r for r in results if r.arrival_mode == "normal"], key=lambda r: r.num_servers)
    peak_pair = sorted([r for r in results if r.arrival_mode == "peak"], key=lambda r: r.num_servers)
    common_servers = {r.num_servers for r in normal_pair} & {r.num_servers for r in peak_pair}
    if common_servers:
        n_list = sorted(common_servers)
        norm = [next(r for r in normal_pair if r.num_servers == s) for s in n_list]
        peak = [next(r for r in peak_pair if r.num_servers == s) for s in n_list]
        plot_peak_hour_analysis(norm, peak, output_dir / "fig5_peak_hour_waiting.png")

    if show:
        plt.show()
