from __future__ import annotations

from collections import deque
from typing import Deque, Dict, List, Tuple


class QueueManager:
    """
    Tracks customers waiting for a server and integrates queue length over time.

    The time-average queue length L is computed as (1/T) * integral of Q(t) dt
    using a standard rectangle rule between state-change events.
    """

    def __init__(self) -> None:
        self._fifo: Deque[int] = deque()
        self._in_system: Dict[int, str] = {}
        self._current_queue_length: int = 0
        self._last_event_time: float = 0.0
        self._area_under_queue_curve: float = 0.0
        self._timeline: List[Tuple[float, int]] = []

    @property
    def current_queue_length(self) -> int:
        return self._current_queue_length

    def _advance_clock(self, timestamp: float) -> None:
        if timestamp < self._last_event_time:
            raise ValueError("Non-monotonic timestamps are not allowed for queue metrics.")
        delta = timestamp - self._last_event_time
        self._area_under_queue_curve += self._current_queue_length * delta
        self._last_event_time = timestamp

    def enter_queue(self, customer_id: int, timestamp: float) -> None:
        """Customer joins the FIFO lane after arrival."""
        self._advance_clock(timestamp)
        self._fifo.append(customer_id)
        self._in_system[customer_id] = "queued"
        self._current_queue_length += 1
        self._timeline.append((timestamp, self._current_queue_length))

    def start_service(self, customer_id: int, timestamp: float) -> None:
        """Customer leaves the visible queue and occupies a server."""
        self._advance_clock(timestamp)
        if not self._fifo or self._fifo[0] != customer_id:
            # Defensive: allow removal if out-of-sync but log inconsistency
            try:
                self._fifo.remove(customer_id)
            except ValueError as exc:
                raise RuntimeError(
                    f"Customer {customer_id} cannot start service; FIFO mismatch."
                ) from exc
        else:
            self._fifo.popleft()
        self._in_system[customer_id] = "in_service"
        self._current_queue_length = max(0, self._current_queue_length - 1)
        self._timeline.append((timestamp, self._current_queue_length))

    def abandon_queue(self, customer_id: int, timestamp: float) -> None:
        """Customer reneges after excessive waiting."""
        self._advance_clock(timestamp)
        try:
            self._fifo.remove(customer_id)
        except ValueError as exc:
            raise RuntimeError(f"Customer {customer_id} not found in FIFO queue.") from exc
        self._in_system.pop(customer_id, None)
        self._current_queue_length = max(0, self._current_queue_length - 1)
        self._timeline.append((timestamp, self._current_queue_length))

    def complete_service(self, customer_id: int, timestamp: float) -> None:
        """Customer finished service and exits."""
        self._advance_clock(timestamp)
        self._in_system.pop(customer_id, None)

    def time_average_queue_length(self, horizon: float) -> float:
        """Little's L: time-average number of customers waiting (not in service)."""
        if horizon <= 0:
            raise ValueError("horizon must be positive to compute L.")
        # Close out the final rectangle up to horizon
        self._advance_clock(horizon)
        return self._area_under_queue_curve / horizon

    def snapshot_timeline(self) -> List[Tuple[float, int]]:
        """Return (time, queue_length) pairs for plotting."""
        return list(self._timeline)
