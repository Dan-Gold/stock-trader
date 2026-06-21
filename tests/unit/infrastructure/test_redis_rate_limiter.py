"""Tests for the Redis-backed sliding-window rate limiter.

Fail-open/closed branches are exercised against a Redis client pointed at a closed
port (``register_script`` does no I/O; the EVALSHA on ``acquire`` raises
``ConnectionError``). The sliding-window and cross-caller property tests need a
real Redis (fakeredis cannot run the Lua/``TIME`` path) and skip when one is not
reachable on ``localhost:6379``.
"""

import os
import threading
import time
from collections.abc import Iterator
from typing import cast
from uuid import uuid4

import pytest
import redis

from stock_trader.core.market_data.providers.massive.rate_limiter import MassiveRateLimiter
from stock_trader.core.market_data.providers.rate_limiter_interface import IRateLimiter
from stock_trader.infrastructure.redis_rate_limiter import RedisSlidingWindowRateLimiter

# Isolated logical DB so flushdb() can't touch the broker/cache.
_TEST_REDIS_DB = 15
# Honour the deployment's Redis host (REDIS_HOST=redis in docker); fall back to
# localhost for ad-hoc local runs. These tests skip when no Redis is reachable.
_TEST_REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
_TEST_REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))


def _unreachable_client() -> redis.Redis:
    """A client whose connection attempts fail fast (closed port 1)."""
    return redis.Redis(host="127.0.0.1", port=1, socket_connect_timeout=0.1, decode_responses=True)


def _real_redis_or_skip() -> redis.Redis:
    """Return a real Redis client on a test DB, or skip if none is reachable."""
    client = redis.Redis(
        host=_TEST_REDIS_HOST,
        port=_TEST_REDIS_PORT,
        db=_TEST_REDIS_DB,
        decode_responses=True,
        socket_connect_timeout=0.5,
    )
    try:
        client.ping()
    except redis.RedisError:
        pytest.skip(f"real Redis not available on {_TEST_REDIS_HOST}:{_TEST_REDIS_PORT}")
    return client


@pytest.fixture()
def real_client() -> Iterator[redis.Redis]:
    """Provide a real Redis client on the test DB, flushed after each test."""
    client = _real_redis_or_skip()
    try:
        yield client
    finally:
        client.flushdb()
        client.close()


class TestConstruction:
    """Constructor validation."""

    def test_rejects_zero_max_requests(self) -> None:
        """max_requests < 1 should raise a ValueError."""
        with pytest.raises(ValueError, match="max_requests"):
            RedisSlidingWindowRateLimiter(_unreachable_client(), key="k", max_requests=0)

    def test_rejects_zero_window(self) -> None:
        """window_seconds < 1 should raise a ValueError."""
        with pytest.raises(ValueError, match="window_seconds"):
            RedisSlidingWindowRateLimiter(_unreachable_client(), key="k", window_seconds=0)


class TestFailMode:
    """Behaviour when Redis is unreachable."""

    def test_fail_closed_raises(self) -> None:
        """fail_open=False should re-raise the Redis error (fail closed)."""
        limiter = RedisSlidingWindowRateLimiter(_unreachable_client(), key="k", fail_open=False)
        with pytest.raises(redis.RedisError):
            limiter.acquire()

    def test_fail_open_allows(self) -> None:
        """fail_open=True should swallow the Redis error and allow the call."""
        limiter = RedisSlidingWindowRateLimiter(_unreachable_client(), key="k", fail_open=True)
        limiter.acquire()  # returns without raising


class TestSlidingWindow:
    """Window behaviour against a real Redis."""

    def test_allows_up_to_max_immediately(self, real_client: redis.Redis) -> None:
        """The first max_requests acquires should not block."""
        limiter = RedisSlidingWindowRateLimiter(real_client, key=f"t:{uuid4().hex}", max_requests=3, window_seconds=60)

        start = time.monotonic()
        for _ in range(3):
            limiter.acquire()

        assert time.monotonic() - start < 0.5

    def test_blocks_when_window_full(self, real_client: redis.Redis) -> None:
        """The (max+1)th acquire should block until the oldest entry expires."""
        limiter = RedisSlidingWindowRateLimiter(real_client, key=f"t:{uuid4().hex}", max_requests=2, window_seconds=2)
        limiter.acquire()
        limiter.acquire()

        start = time.monotonic()
        limiter.acquire()  # must wait for the first entry to leave the 2s window

        assert time.monotonic() - start >= 1.0

    def test_sets_key_ttl(self, real_client: redis.Redis) -> None:
        """A reserve should set a positive TTL on the key."""
        key = f"t:{uuid4().hex}"
        limiter = RedisSlidingWindowRateLimiter(real_client, key=key, max_requests=5, window_seconds=60)

        limiter.acquire()

        assert cast(int, real_client.pttl(key)) > 0

    def test_cross_caller_shared_window(self, real_client: redis.Redis) -> None:
        """Concurrent callers share one budget: at most max_requests proceed at once."""
        max_requests = 3
        limiter = RedisSlidingWindowRateLimiter(
            real_client, key=f"t:{uuid4().hex}", max_requests=max_requests, window_seconds=3
        )
        completions: list[float] = []
        lock = threading.Lock()

        def worker() -> None:
            limiter.acquire()
            with lock:
                completions.append(time.monotonic())

        threads = [threading.Thread(target=worker) for _ in range(max_requests * 2)]
        start = time.monotonic()
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=15)

        assert len(completions) == max_requests * 2  # all eventually proceed
        immediate = [c for c in completions if c - start < 1.0]
        assert len(immediate) <= max_requests  # the shared window caps the first batch


@pytest.fixture(params=["in_memory", "redis"])
def conformance_limiter(request: pytest.FixtureRequest) -> Iterator[IRateLimiter]:
    """Yield each IRateLimiter implementation for shared contract tests."""
    if request.param == "in_memory":
        yield MassiveRateLimiter(max_requests=5, window_seconds=60)
        return
    client = _real_redis_or_skip()
    try:
        yield RedisSlidingWindowRateLimiter(client, key=f"t:{uuid4().hex}", max_requests=5, window_seconds=60)
    finally:
        client.flushdb()
        client.close()


class TestIRateLimiterConformance:
    """Contract both limiters must satisfy."""

    def test_allows_up_to_max_immediately(self, conformance_limiter: IRateLimiter) -> None:
        """acquire() must not block while under budget, for either implementation."""
        start = time.monotonic()
        for _ in range(5):
            conformance_limiter.acquire()

        assert time.monotonic() - start < 0.5
