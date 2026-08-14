"""
Central configuration for the drive-through discrete-event simulation.

All tunable parameters live here so experiments stay reproducible and
easy to document for academic reports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SimulationConfig:
    """Parameters governing the simulation horizon, traffic, and economics."""

    # Time horizon (minutes) — interpret as abstract time units if preferred.
    simulation_duration: float = 480.0  # 8-hour operating day

    # Poisson arrival rate (customers per minute). Higher => busier system.
    normal_arrival_rate: float = 0.35
    peak_arrival_rate: float = 0.85

    # Exponential service rate (1 / mean service time in minutes).
    service_rate: float = 0.5  # mean service = 2 minutes

    # Maximum time (minutes) a customer will wait in queue before reneging.
    max_wait_before_renege: float = 8.0

    # Revenue model: fixed ticket price for lost-sale estimation.
    average_ticket_price: float = 9.50

    # Randomness control
    random_seed: Optional[int] = 42

    # Output locations (created automatically when needed)
    output_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent / "outputs")

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if self.simulation_duration <= 0:
            raise ValueError("simulation_duration must be positive.")
        if self.normal_arrival_rate <= 0 or self.peak_arrival_rate <= 0:
            raise ValueError("Arrival rates must be positive.")
        if self.service_rate <= 0:
            raise ValueError("service_rate must be positive.")
        if self.max_wait_before_renege <= 0:
            raise ValueError("max_wait_before_renege must be positive.")
        if self.average_ticket_price < 0:
            raise ValueError("average_ticket_price cannot be negative.")

    @property
    def mean_service_time(self) -> float:
        """Mean of the exponential service-time distribution (minutes)."""
        return 1.0 / self.service_rate
