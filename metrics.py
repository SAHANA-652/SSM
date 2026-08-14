from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class ScenarioResult:
    """One row of KPIs after a simulation replication."""

    scenario_name: str
    num_servers: int
    arrival_mode: str  # "normal" or "peak"
    completed_customers: int
    lost_customers: int
    average_waiting_time: float
    time_average_queue_length: float
    throughput_per_hour: float
    server_utilization: float
    lost_revenue: float
    simulation_duration: float
    random_seed: Optional[int] = None
    queue_timeline: Optional[List[Tuple[float, int]]] = None


@dataclass
class MetricsTracker:
    """Accumulates per-customer measurements during a SimPy run."""

    waiting_times: List[float] = field(default_factory=list)
    system_times: List[float] = field(default_factory=list)
    lost_customers: int = 0
    completed_customers: int = 0
    total_service_minutes: float = 0.0

    def record_completed_trip(self, wait: float, system_time: float, service_minutes: float) -> None:
        self.waiting_times.append(wait)
        self.system_times.append(system_time)
        self.total_service_minutes += service_minutes
        self.completed_customers += 1

    def record_lost_customer(self) -> None:
        self.lost_customers += 1

    def summary(self) -> Dict[str, float]:
        waits = np.array(self.waiting_times, dtype=float)
        sys_times = np.array(self.system_times, dtype=float)
        return {
            "completed": float(self.completed_customers),
            "lost": float(self.lost_customers),
            "avg_wait": float(waits.mean()) if waits.size else 0.0,
            "std_wait": float(waits.std(ddof=1)) if waits.size > 1 else 0.0,
            "p95_wait": float(np.percentile(waits, 95)) if waits.size else 0.0,
            "avg_system_time": float(sys_times.mean()) if sys_times.size else 0.0,
            "total_service_minutes": float(self.total_service_minutes),
        }


def results_to_dataframe(results: List[ScenarioResult]) -> pd.DataFrame:
    """Convert scenario outputs to a pandas DataFrame."""
    rows = [r.__dict__ for r in results]
    return pd.DataFrame(rows)


def export_results_csv(results: List[ScenarioResult], path: Path) -> None:
    """Persist KPI table for spreadsheets or further analysis."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        df = results_to_dataframe(results)
        if "queue_timeline" in df.columns:
            df = df.drop(columns=["queue_timeline"])
        df.to_csv(path, index=False)
    except OSError as exc:
        raise RuntimeError(f"Unable to write CSV to {path}") from exc
