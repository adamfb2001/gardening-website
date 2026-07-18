"""Per-device sliding-window rate limiting (spec §6: 30 jobs/hour, 200/day).

In-memory, like the M1 job store; both move to shared storage together when
the backend scales past one process.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Callable, Optional

_HOUR = 3600.0
_DAY = 86400.0


class RateLimiter:
    def __init__(
        self,
        per_hour: int,
        per_day: int,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._per_hour = per_hour
        self._per_day = per_day
        self._clock = clock
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def try_acquire(self, device_id: str) -> Optional[float]:
        """Record one enqueue for the device if allowed.

        Returns None when allowed, otherwise the seconds until the next
        slot frees up (for the Retry-After header). Only successful new-job
        submissions are recorded; callers must not charge idempotent replays.
        """
        now = self._clock()
        events = self._events[device_id]
        while events and events[0] <= now - _DAY:
            events.popleft()

        if len(events) >= self._per_day:
            return events[0] + _DAY - now

        in_last_hour = [t for t in events if t > now - _HOUR]
        if len(in_last_hour) >= self._per_hour:
            return in_last_hour[0] + _HOUR - now

        events.append(now)
        return None
