"""
Customer entity for the drive-through model.

Keeps lightweight state used by metrics and tracing; the heavy lifting is in
SimPy processes inside :mod:`simulation`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Customer:
    """Represents one vehicle / customer traversing the drive-through."""

    customer_id: int
    arrival_time: float
    service_start_time: Optional[float] = None
    departure_time: Optional[float] = None
    abandoned: bool = False
    notes: str = field(default="", repr=False)

    @property
    def waiting_time(self) -> Optional[float]:
        """Time from arrival until service begins (None if never served)."""
        if self.service_start_time is None:
            return None
        return self.service_start_time - self.arrival_time

    @property
    def system_time(self) -> Optional[float]:
        """Total time inside the system (queue + service) for completed trips."""
        if self.departure_time is None or self.service_start_time is None:
            return None
        return self.departure_time - self.arrival_time


class CustomerFactory:
    """Issues monotonically increasing customer identifiers."""

    def __init__(self) -> None:
        self._next_id = 1

    def create(self, arrival_time: float) -> Customer:
        cid = self._next_id
        self._next_id += 1
        return Customer(customer_id=cid, arrival_time=arrival_time)
