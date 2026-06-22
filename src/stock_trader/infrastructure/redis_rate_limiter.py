"""Redis-backed cross-process sliding-window rate limiter for the Massive API.

Replaces the in-process :class:`MassiveRateLimiter` (whose sliding window is
instance-local) with a limiter whose window lives in Redis, so a single budget
is shared across every process and gevent greenlet that calls the provider.

The check-evict-reserve is a single atomic Lua script keyed on a shared Redis
key and timed by the Redis server clock (``TIME``), which makes the limit correct
across processes and eliminates client clock skew.
"""

import logging
import random
import time
from functools import lru_cache
from uuid import uuid4

import redis

from stock_trader.core.market_data.providers.rate_limiter_interface import IRateLimiter
from stock_trader.entrypoints.config import get_config

logger = logging.getLogger(__name__)

# Atomic check-evict-reserve. Uses the Redis server clock (TIME) as the single
# source of truth across all callers. Returns 0 if a slot was reserved, else the
# number of milliseconds to wait before the oldest entry leaves the window.
_ACQUIRE_LUA = """
local key          = KEYS[1]
local max_requests = tonumber(ARGV[1])
local window_ms    = tonumber(ARGV[2])
local member       = ARGV[3]

local t   = redis.call('TIME')                 -- {seconds, microseconds}
local now = (tonumber(t[1]) * 1000) + math.floor(tonumber(t[2]) / 1000)

redis.call('ZREMRANGEBYSCORE', key, 0, now - window_ms)
local count = redis.call('ZCARD', key)

if count < max_requests then
    redis.call('ZADD', key, now, member)
    redis.call('PEXPIRE', key, window_ms)
    return 0
end

local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
local wait   = (tonumber(oldest[2]) + window_ms) - now
if wait < 1 then wait = 1 end
return wait
"""

# Largest random jitter (seconds) added to a waiter's sleep to de-synchronize
# wake-ups under contention (thundering herd).
_MAX_JITTER_SECONDS = 0.25

# Namespace for the limiter's Redis key, keeping it clear of cache/broker keys.
_KEY_PREFIX = "ratelimit"


class RedisSlidingWindowRateLimiter(IRateLimiter):
    """Cross-process sliding-window rate limiter backed by Redis.

    Conforms to :class:`IRateLimiter`: :meth:`acquire` blocks (sleeps) until a
    slot is free. Correct across processes and greenlets because the
    check-evict-reserve runs as a single atomic Lua script against a shared Redis
    key, timed by the Redis server clock (so there is no client clock skew).

    Membership is bounded: a member is only added when the window has room, so the
    sorted set holds at most ``max_requests`` entries per window.

    Args:
        client: A (sync) Redis client. ``acquire`` is synchronous and runs inside
            sync Celery tasks, so a sync client is required.
        key: The shared Redis key for this provider+window. All callers must use
            the same key for the budget to be shared.
        max_requests: Maximum requests allowed within the sliding window.
        window_seconds: Size of the sliding window in seconds.
        fail_open: Behaviour when Redis is unreachable. ``False`` (the default)
            fails closed — :meth:`acquire` re-raises the Redis error rather than
            allowing an unmetered call. ``True`` fails open (allows the call and
            logs a warning).
    """

    def __init__(
        self,
        client: redis.Redis,
        key: str,
        max_requests: int = 5,
        window_seconds: int = 60,
        fail_open: bool = False,
    ) -> None:
        if max_requests < 1:
            raise ValueError("max_requests must be >= 1")
        if window_seconds < 1:
            raise ValueError("window_seconds must be >= 1")

        self._client = client
        self._key = key
        self._max_requests = max_requests
        self._window_ms = window_seconds * 1000
        self._fail_open = fail_open
        # register_script caches the script SHA and issues EVALSHA, transparently
        # falling back to EVAL on NOSCRIPT — no manual SHA management required.
        self._script = client.register_script(_ACQUIRE_LUA)

    def acquire(self) -> None:
        """Acquire a rate limit slot, blocking until one is available.

        Runs the atomic reserve script; on success returns immediately, otherwise
        sleeps for the script-computed wait (plus jitter) and retries.

        Raises:
            redis.RedisError: If Redis is unreachable and ``fail_open`` is False
                (fail-closed). The caller is expected to treat this as a
                retryable failure.
        """
        while True:
            try:
                member = uuid4().hex  # uniqueness is load-bearing for ZCARD counting
                # KEYS[1] = the shared limiter key; ARGV = [max_requests, window_ms,
                # unique member]. Returns 0 if a slot was reserved, else the ms to
                # wait until the oldest entry leaves the window.
                wait_ms = int(self._script(keys=[self._key], args=[self._max_requests, self._window_ms, member]))

            except redis.RedisError:
                if self._fail_open:
                    logger.warning("Rate limiter Redis error on %s; failing open (allowing call)", self._key)
                    return

                logger.error("Rate limiter Redis error on %s; failing closed (raising)", self._key)
                raise

            if wait_ms == 0:
                return

            # Jitter de-synchronizes waiters that would otherwise wake together and
            # re-EVAL in lockstep (thundering herd) under sustained contention.
            sleep_s = (wait_ms / 1000) + random.uniform(0, _MAX_JITTER_SECONDS)
            logger.info("Rate limit reached on %s; sleeping %.2fs", self._key, sleep_s)
            time.sleep(sleep_s)


@lru_cache(maxsize=1)
def build_massive_rate_limiter() -> RedisSlidingWindowRateLimiter:
    """Build (and cache) the shared Massive rate limiter from application config.

    Cached per process: the gevent fetch worker is long-lived, so one limiter —
    and therefore one Redis client and connection pool, with the script registered
    once — is shared across all its greenlets and tasks. ``max_connections`` gives
    concurrent ``acquire`` calls a connection without serializing on checkout. The
    client is created lazily on first use, so prefork children build their own
    post-fork rather than inheriting a shared socket.

    Returns:
        A configured :class:`RedisSlidingWindowRateLimiter`.
    """
    cfg = get_config()
    client = redis.Redis(
        host=cfg.redis_host,
        port=cfg.redis_port,
        db=cfg.redis_db,
        decode_responses=True,
        max_connections=8,
    )
    return RedisSlidingWindowRateLimiter(
        client=client,
        key=f"{_KEY_PREFIX}:massive:{cfg.massive_rate_window_seconds}",
        max_requests=cfg.massive_rate_max_requests,
        window_seconds=cfg.massive_rate_window_seconds,
        fail_open=cfg.ratelimit_fail_open,
    )
