"""Rate limiter interface for market data providers."""

from typing import Protocol


class IRateLimiter(Protocol):
    """Protocol for rate limiters.

    Each market data provider can have its own rate limiter implementation
    (in-memory sliding window, Redis-backed, token bucket, etc.) as long
    as it satisfies this interface.
    """

    def acquire(self) -> None:
        """Acquire a rate limit slot, blocking if necessary.

        Implementations should block (sleep) until a slot is available
        rather than raising an exception.
        """
        ...
