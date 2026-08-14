"""
Core SimPy model for the drive-through: arrivals, FIFO queue, parallel servers,
exponential service times, and impatient customers (lost sales).
"""

from __future__ import annotations

import random
from typing import Iterator, List, Optional, Tuple

import numpy as np
import simpy

from config import SimulationConfig
from customer import Customer, CustomerFactory
from metrics import MetricsTracker, ScenarioResult
from queue_manager import QueueManager


class DriveThroughSystem:
    """
    Encapsulates the discrete-event simulation.

    Each run uses a fresh SimPy environment so scenarios remain independent.
    """

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config
        self.env: simpy.Environment = simpy.Environment()
        self.resource: simpy.Resource = simpy.Resource(self.env, capacity=1)
        self.queue_mgr = QueueManager()
        self.metrics = MetricsTracker()
        self.factory = CustomerFactory()
        self.rng = np.random.default_rng(config.random_seed)
        if config.random_seed is not None:
            random.seed(config.random_seed)

    def _reset(self, num_servers: int) -> None:
        self.env = simpy.Environment()
        self.resource = simpy.Resource(self.env, capacity=max(1, num_servers))
        self.queue_mgr = QueueManager()
        self.metrics = MetricsTracker()
        self.factory = CustomerFactory()
        self.rng = np.random.default_rng(self.config.random_seed)

    def _arrival_rate(self, mode: str) -> float:
        if mode == "normal":
            return self.config.normal_arrival_rate
        if mode == "peak":
            return self.config.peak_arrival_rate
        raise ValueError("mode must be 'normal' or 'peak'.")

    def _spawn_arrivals(self, mode: str) -> Iterator[simpy.events.Event]:
        """Poisson arrivals via exponential inter-arrival times (minutes)."""
        arrival_rate = self._arrival_rate(mode)
        while True:
            inter_arrival = float(self.rng.exponential(1.0 / arrival_rate))
            if self.env.now + inter_arrival > self.config.simulation_duration:
                break
            yield self.env.timeout(inter_arrival)
            if self.env.now > self.config.simulation_duration:
                break
            customer = self.factory.create(self.env.now)
            self.env.process(self._customer_journey(customer))

    def _customer_journey(self, customer: Customer) -> Iterator[simpy.events.Event]:
        """Customer lifecycle: queue -> (renege?) -> service -> exit."""
        arrival_time = self.env.now
        try:
            self.queue_mgr.enter_queue(customer.customer_id, arrival_time)
        except ValueError as exc:
            raise RuntimeError("QueueManager clock error during enter_queue.") from exc

        patience = self.config.max_wait_before_renege

        with self.resource.request() as req:
            result = yield req | self.env.timeout(patience)
            if req not in result:
                customer.abandoned = True
                now = self.env.now
                try:
                    self.queue_mgr.abandon_queue(customer.customer_id, now)
                except RuntimeError:
                    # Keep KPIs consistent even if FIFO bookkeeping drifts.
                    pass
                self.metrics.record_lost_customer()
                return

            service_start = self.env.now
            customer.service_start_time = service_start
            wait = service_start - arrival_time

            try:
                self.queue_mgr.start_service(customer.customer_id, service_start)
            except RuntimeError as exc:
                raise RuntimeError("FIFO bookkeeping failed at service start.") from exc

            # Exponential service times (mean = mean_service_time).
            service_duration = float(self.rng.exponential(self.config.mean_service_time))
            yield self.env.timeout(service_duration)

            departure = self.env.now
            customer.departure_time = departure
            system_time = departure - arrival_time

            try:
                self.queue_mgr.complete_service(customer.customer_id, departure)
            except ValueError as exc:
                raise RuntimeError("QueueManager clock error during complete_service.") from exc

            self.metrics.record_completed_trip(
                wait=wait,
                system_time=system_time,
                service_minutes=service_duration,
            )

    def run(
        self,
        num_servers: int,
        mode: str = "normal",
        scenario_name: Optional[str] = None,
        attach_queue_timeline: bool = False,
    ) -> ScenarioResult:
        """
        Execute one simulation replication.

        Parameters
        ----------
        num_servers:
            Number of parallel drive-through windows (1, 2, 3, ...).
        mode:
            ``"normal"`` or ``"peak"`` arrival intensity.
        scenario_name:
            Optional label for reporting; defaults to ``f"{mode}_{num_servers}S"``.
        attach_queue_timeline:
            If True, store ``(time, queue_length)`` samples on the result for plotting.
        """

        if num_servers < 1:
            raise ValueError("num_servers must be at least 1.")

        self._reset(num_servers)
        self.env.process(self._spawn_arrivals(mode))
        try:
            self.env.run(until=self.config.simulation_duration)
        except Exception as exc:
            raise RuntimeError("SimPy environment failed while executing events.") from exc

        horizon = self.config.simulation_duration
        avg_queue_length = self.queue_mgr.time_average_queue_length(horizon)

        duration_hours = horizon / 60.0 if horizon > 0 else 0.0
        throughput_per_hour = (
            self.metrics.completed_customers / duration_hours if duration_hours > 0 else 0.0
        )

        utilization = 0.0
        if horizon > 0 and num_servers > 0:
            utilization = min(
                1.0,
                self.metrics.total_service_minutes / (num_servers * horizon),
            )

        summary = self.metrics.summary()
        lost_revenue = self.metrics.lost_customers * self.config.average_ticket_price

        label = scenario_name or f"{mode}_{num_servers}S"

        timeline: Optional[List[Tuple[float, int]]] = None
        if attach_queue_timeline:
            timeline = self.queue_mgr.snapshot_timeline()

        return ScenarioResult(
            scenario_name=label,
            num_servers=num_servers,
            arrival_mode=mode,
            completed_customers=self.metrics.completed_customers,
            lost_customers=self.metrics.lost_customers,
            average_waiting_time=float(summary["avg_wait"]),
            time_average_queue_length=float(avg_queue_length),
            throughput_per_hour=float(throughput_per_hour),
            server_utilization=float(utilization),
            lost_revenue=float(lost_revenue),
            simulation_duration=horizon,
            random_seed=self.config.random_seed,
            queue_timeline=timeline,
        )
