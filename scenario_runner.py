"""
Shared scenario batch for CLI and web UI (single source of truth for experiment design).
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from config import SimulationConfig
from metrics import ScenarioResult
from simulation import DriveThroughSystem


def run_standard_scenarios(config: SimulationConfig) -> tuple[List[ScenarioResult], Dict[str, List[Tuple[float, int]]]]:
    """
    Run 1–3 servers under normal traffic (with queue timelines for 1 and 3 windows),
    then 1–3 servers under peak traffic.

    Returns
    -------
    results :
        Six ``ScenarioResult`` rows (normal_1S … peak_3S).
    queue_series :
        Labels mapped to ``(time, queue_length)`` samples for plotting.
    """
    system = DriveThroughSystem(config)
    results: List[ScenarioResult] = []

    for servers in (1, 2, 3):
        results.append(
            system.run(
                num_servers=servers,
                mode="normal",
                scenario_name=f"normal_{servers}S",
                attach_queue_timeline=servers in (1, 3),
            )
        )

    for servers in (1, 2, 3):
        results.append(
            system.run(
                num_servers=servers,
                mode="peak",
                scenario_name=f"peak_{servers}S",
                attach_queue_timeline=False,
            )
        )

    series: Dict[str, List[Tuple[float, int]]] = {}
    for r in results:
        if r.queue_timeline:
            label = f"{r.num_servers} window(s) — {r.arrival_mode} traffic"
            series[label] = list(r.queue_timeline)

    return results, series
