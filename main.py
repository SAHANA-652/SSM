from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

import pandas as pd

from config import SimulationConfig
from metrics import ScenarioResult, export_results_csv, results_to_dataframe
from scenario_runner import run_standard_scenarios
from visualization import generate_all_figures


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Drive-through DES study — wait times, queueing, and lost sales.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Simulation horizon in minutes (default: value from SimulationConfig).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility (default: config value).",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Display Matplotlib windows after saving figures.",
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Skip figure generation (CSV/text only).",
    )
    return parser.parse_args()


def _print_console_report(results: List[ScenarioResult]) -> None:
    """Human-readable KPI table for demos and quick inspection."""
    df = results_to_dataframe(results)
    if "queue_timeline" in df.columns:
        df = df.drop(columns=["queue_timeline"])
    with pd.option_context("display.max_rows", None, "display.width", 120):
        print("\n=== Scenario KPI Summary ===\n")
        print(df.to_string(index=False, float_format=lambda x: f"{x:,.3f}"))


def main() -> int:
    args = _parse_args()

    try:
        config = SimulationConfig()
        if args.duration is not None:
            config.simulation_duration = args.duration
        if args.seed is not None:
            config.random_seed = args.seed

        results, queue_series = run_standard_scenarios(config)

        out_dir = Path(config.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        export_results_csv(results, out_dir / "scenario_results.csv")

        _print_console_report(results)

        print("\n=== Interpretation (quick) ===")
        best = min((r for r in results if r.arrival_mode == "normal"), key=lambda r: r.average_waiting_time)
        print(
            f"- Under normal traffic, '{best.scenario_name}' yields the lowest average wait "
            f"({best.average_waiting_time:.2f} min) among 1-3 windows."
        )
        worst_peak = max((r for r in results if r.arrival_mode == "peak"), key=lambda r: r.lost_customers)
        print(
            f"- Peak traffic sees the most lost customers in '{worst_peak.scenario_name}' "
            f"({worst_peak.lost_customers} losses, ~${worst_peak.lost_revenue:,.2f} estimated revenue at risk)."
        )

        if not args.no_plots:
            generate_all_figures(
                results=results,
                queue_series=queue_series,
                horizon_minutes=config.simulation_duration,
                output_dir=out_dir,
                show=args.show,
            )
            print(f"\nFigures saved under: {out_dir.resolve()}")
            print("CSV written to: scenario_results.csv")

        print("\nRun finished successfully.\n")
        return 0

    except Exception as exc:  # noqa: BLE001 — top-level guard for student-friendly errors
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
