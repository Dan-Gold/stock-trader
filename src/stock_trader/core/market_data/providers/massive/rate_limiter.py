"""In-memory sliding window rate limiter for the Massive API.

Tracks API call timestamps and sleeps when the limit would be exceeded.
Works well for single-process workers (worker_concurrency=1). For
multi-worker setups, swap to a Redis-backed implementation.

Massive free-tier limit: 5 requests per 60 seconds.
"""

import logging
import time
from collections import deque

logger = logging.getLogger(__name__)

# Massive free-tier defaults
DEFAULT_MAX_REQUESTS = 5
DEFAULT_WINDOW_SECONDS = 60


class MassiveRateLimiter:
    """Sliding window rate limiter for the Massive API.

    Enforces a maximum number of requests within a rolling time window.
    When the limit is reached, ``acquire()`` blocks (sleeps) until
    a slot opens up.

    Args:
        max_requests: Maximum requests allowed in the sliding window.
        window_seconds: Size of the sliding window in seconds.

    Example::

        limiter = MassiveRateLimiter()  # 5 req / 60s

        for symbol in symbols:
            limiter.acquire()          # blocks if 5 calls were made in the last 60s
            provider.fetch_ohlcv(...)  # safe to call
    """

    def __init__(
        self,
        max_requests: int = DEFAULT_MAX_REQUESTS,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
    ) -> None:
        if max_requests < 1:
            raise ValueError("max_requests must be >= 1")
        if window_seconds < 1:
            raise ValueError("window_seconds must be >= 1")

        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps: deque[float] = deque()

    def acquire(self) -> None:
        """Acquire a rate limit slot, blocking if necessary.

        Evicts expired timestamps, then sleeps if the window is full.
        Records the call timestamp before returning.
        """
        self._evict_expired()

        if len(self._timestamps) >= self.max_requests:
            oldest = self._timestamps[0]
            sleep_time = self.window_seconds - (time.monotonic() - oldest)

            if sleep_time > 0:
                logger.info(
                    "Rate limit reached (%d/%d). Sleeping %.1fs",
                    len(self._timestamps),
                    self.max_requests,
                    sleep_time,
                )
                time.sleep(sleep_time)
                self._evict_expired()

        self._timestamps.append(time.monotonic())

    def _evict_expired(self) -> None:
        """Remove timestamps outside the sliding window."""
        cutoff = time.monotonic() - self.window_seconds
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()
