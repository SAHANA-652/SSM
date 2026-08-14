from __future__ import annotations

import io
from typing import List, Optional

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from config import SimulationConfig
from metrics import ScenarioResult, results_to_dataframe
from scenario_runner import run_standard_scenarios
from visualization import (
    plot_lost_customers_bar,
    plot_peak_hour_analysis,
    plot_queue_length_timeseries,
    plot_throughput_comparison,
    plot_waiting_time_vs_servers,
)


def _build_config_from_sidebar() -> SimulationConfig:
    """Instantiate ``SimulationConfig`` from sidebar widgets."""
    duration = st.sidebar.number_input(
        "Simulation duration (minutes)",
        min_value=30.0,
        max_value=2880.0,
        value=480.0,
        step=30.0,
        help="Total clock time for one replication (e.g. 480 = 8 hours).",
    )
    lam_n = st.sidebar.number_input(
        "Normal arrival rate (customers / minute)",
        min_value=0.05,
        max_value=5.0,
        value=0.35,
        step=0.05,
        format="%.2f",
    )
    lam_p = st.sidebar.number_input(
        "Peak arrival rate (customers / minute)",
        min_value=0.05,
        max_value=5.0,
        value=0.85,
        step=0.05,
        format="%.2f",
    )
    mu = st.sidebar.number_input(
        "Service rate (1 / mean service minutes)",
        min_value=0.1,
        max_value=3.0,
        value=0.5,
        step=0.05,
        format="%.2f",
    )
    max_wait = st.sidebar.number_input(
        "Max wait before reneging (minutes)",
        min_value=0.5,
        max_value=60.0,
        value=8.0,
        step=0.5,
    )
    ticket = st.sidebar.number_input(
        "Average ticket price ($)",
        min_value=0.0,
        max_value=100.0,
        value=9.50,
        step=0.25,
        format="%.2f",
    )
    seed_in = st.sidebar.text_input(
        "Random seed (blank = random each run)",
        value="42",
        help="Integer seed for reproducible results; leave empty for nondeterministic runs.",
    )
    seed: Optional[int]
    if seed_in.strip() == "":
        seed = None
    else:
        try:
            seed = int(seed_in.strip())
        except ValueError as exc:
            raise ValueError("Random seed must be an integer or empty.") from exc

    return SimulationConfig(
        simulation_duration=float(duration),
        normal_arrival_rate=float(lam_n),
        peak_arrival_rate=float(lam_p),
        service_rate=float(mu),
        max_wait_before_renege=float(max_wait),
        average_ticket_price=float(ticket),
        random_seed=seed,
    )


def _results_to_download_df(results: List[ScenarioResult]) -> pd.DataFrame:
    df = results_to_dataframe(results)
    if "queue_timeline" in df.columns:
        df = df.drop(columns=["queue_timeline"])
    return df


def main() -> None:
    st.set_page_config(
        page_title="Drive-Through DES",
        page_icon="🍔",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("Fast-food drive-through — discrete-event simulation")
    st.markdown(
        "Poisson arrivals, **FIFO** queue, **exponential** service times, "
        "**multi-window** (1–3 servers), **reneging** (lost sales), and **peak vs normal** traffic."
    )

    try:
        config = _build_config_from_sidebar()
    except ValueError as e:
        st.sidebar.error(str(e))
        st.stop()

    st.sidebar.markdown("---")
    run = st.sidebar.button("Run simulation", type="primary", use_container_width=True)

    if not run and "last_results" not in st.session_state:
        st.info("Set parameters in the sidebar and click **Run simulation**.")
        return

    if run:
        with st.spinner("Running SimPy model (six scenarios)…"):
            try:
                results, queue_series = run_standard_scenarios(config)
            except Exception as e:  # noqa: BLE001
                st.error(f"Simulation failed: {e}")
                st.stop()
        st.session_state["last_results"] = results
        st.session_state["last_queue_series"] = queue_series
        st.session_state["last_config"] = config
    else:
        results = st.session_state["last_results"]
        queue_series = st.session_state["last_queue_series"]
        config = st.session_state["last_config"]

    df = _results_to_download_df(results)
    st.subheader("KPI summary")
    st.dataframe(df, use_container_width=True, hide_index=True)

    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)
    st.download_button(
        label="Download results as CSV",
        data=csv_buf.getvalue(),
        file_name="scenario_results.csv",
        mime="text/csv",
    )

    normal_results = sorted([r for r in results if r.arrival_mode == "normal"], key=lambda r: r.num_servers)
    peak_results = sorted([r for r in results if r.arrival_mode == "peak"], key=lambda r: r.num_servers)

    st.subheader("Charts (Matplotlib)")

    c1, c2 = st.columns(2)
    with c1:
        fig1 = plot_waiting_time_vs_servers(results, output_path=None, arrival_mode="normal")
        st.pyplot(fig1)
        plt.close(fig1)
    with c2:
        fig2 = plot_queue_length_timeseries(
            queue_series,
            output_path=None,
            horizon_minutes=config.simulation_duration,
        )
        st.pyplot(fig2)
        plt.close(fig2)

    c3, c4 = st.columns(2)
    with c3:
        fig3 = plot_lost_customers_bar(results, output_path=None)
        st.pyplot(fig3)
        plt.close(fig3)
    with c4:
        fig4 = plot_throughput_comparison(results, output_path=None)
        st.pyplot(fig4)
        plt.close(fig4)

    common = {r.num_servers for r in normal_results} & {r.num_servers for r in peak_results}
    if common:
        n_list = sorted(common)
        norm = [next(r for r in normal_results if r.num_servers == s) for s in n_list]
        peak = [next(r for r in peak_results if r.num_servers == s) for s in n_list]
        fig5 = plot_peak_hour_analysis(norm, peak, output_path=None)
        st.pyplot(fig5)
        plt.close(fig5)

    st.caption(
        f"Horizon: {config.simulation_duration:.0f} min · "
        f"Mean service: {config.mean_service_time:.2f} min · "
        f"Seed: {config.random_seed}"
    )


if __name__ == "__main__":
    main()
