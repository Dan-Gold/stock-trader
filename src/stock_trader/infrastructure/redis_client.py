"""Redis client interface and implementation for stock trader application."""

from typing import Protocol

from redis.asyncio import Redis


class IRedisClient(Protocol):
    """Interface for Redis client operations."""

    def get_redis_url(self) -> str:
        """Get the Redis connection URL."""
        ...

    # Queue operations
    async def enqueue(self, queue: str, value: str) -> None:
        """Add item to queue."""
        ...

    async def dequeue(self, queue: str, timeout: int = 0) -> str | None:
        """Pop item from queue (blocking)."""
        ...

    async def queue_length(self, queue: str) -> int:
        """Get queue length."""
        ...

    # Cache operations
    async def get(self, key: str) -> str | None:
        """Get cached value."""
        ...

    async def set(self, key: str, value: str, ttl: int | None = 3600) -> None:
        """Set cached value with optional TTL."""
        ...

    async def delete(self, key: str) -> bool:
        """Delete key."""
        ...

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        ...


class RedisClient:
    """Async Redis client for queue and cache operations."""

    def __init__(
        self,
        host: str = "redis",
        port: int = 6379,
        db: int = 0,
        decode_responses: bool = True,
    ) -> None:
        """Initialize the Redis client configuration.

        Args:
            host: Redis server hostname.
            port: Redis server port.
            db: Redis database number.
            decode_responses: Whether to decode byte responses to strings.
        """
        self.host = host
        self.port = port
        self.db = db
        self.decode_responses = decode_responses
        self._client: Redis | None = None

    def get_redis_url(self) -> str:
        """Get the Redis connection URL."""
        return f"redis://{self.host}:{self.port}/{self.db}"

    async def connect(self) -> None:
        """Establish connection to Redis."""
        if self._client is None:
            self._client = Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=self.decode_responses,
            )

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> Redis:
        """Get the Redis client, raising if not connected."""
        if self._client is None:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        return self._client

    # =========================================================================
    # Queue Operations
    # =========================================================================

    async def enqueue(self, queue: str, value: str) -> None:
        """Add an item to the left of a queue (LPUSH).

        Args:
            queue: Name of the queue.
            value: Value to add.
        """
        await self.client.lpush(queue, value)

    async def dequeue(self, queue: str, timeout: int = 0) -> str | None:
        """Pop an item from the right of a queue (BRPOP - blocking).

        Args:
            queue: Name of the queue.
            timeout: Seconds to wait (0 = block forever).

        Returns:
            The popped value, or None if timeout reached.
        """
        result = await self.client.brpop([queue], timeout=timeout)
        return result[1] if result else None

    async def queue_length(self, queue: str) -> int:
        """Get the number of items in a queue.

        Args:
            queue: Name of the queue.

        Returns:
            Number of items in the queue.
        """
        return await self.client.llen(queue)

    # =========================================================================
    # Cache Operations
    # =========================================================================

    async def get(self, key: str) -> str | None:
        """Get a cached value by key.

        Args:
            key: The cache key.

        Returns:
            The cached value, or None if not found.
        """
        return await self.client.get(key)

    async def set(self, key: str, value: str, ttl: int | None = 3600) -> None:
        """Set a cached value with optional TTL.

        Args:
            key: The cache key.
            value: The value to cache.
            ttl: Time-to-live in seconds (default is 3600 seconds), can be None for no expiry.
        """
        if ttl is not None:
            await self.client.set(key, value, ex=ttl)
        else:
            await self.client.set(key, value)

    async def delete(self, key: str) -> bool:
        """Delete a key from cache.

        Args:
            key: The cache key.

        Returns:
            True if key was deleted, False if it didn't exist.
        """
        result = await self.client.delete(key)
        return result > 0

    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache.

        Args:
            key: The cache key.

        Returns:
            True if key exists, False otherwise.
        """
        result = await self.client.exists(key)
        return result > 0


class DisabledRedisClient:
    """Disabled Redis client that raises on any operation."""

    def __init__(
        self,
        host: str = "redis",
        port: int = 6379,
        db: int = 0,
        decode_responses: bool = True,
    ) -> None:
        """Initialize the Redis client configuration.

        Args:
            host: Redis server hostname.
            port: Redis server port.
            db: Redis database number.
            decode_responses: Whether to decode byte responses to strings.
        """
        self.host = host
        self.port = port
        self.db = db
        self.decode_responses = decode_responses
        self._client: Redis | None = None

    def get_redis_url(self) -> str:
        """Get the Redis connection URL."""
        return f"redis://{self.host}:{self.port}/{self.db}"

    async def connect(self) -> None:
        """Establish connection to Redis."""
        pass

    async def close(self) -> None:
        """Close the Redis connection."""
        pass

    # =========================================================================
    # Queue Operations
    # =========================================================================

    async def enqueue(self, queue: str, value: str) -> None:
        """Add an item to the left of a queue (LPUSH)."""
        pass

    async def dequeue(self, queue: str, timeout: int = 0) -> str | None:
        """Pop an item from the right of a queue (BRPOP - blocking)."""
        pass

    async def queue_length(self, queue: str) -> int:
        """Get the number of items in a queue."""
        return 0

    # =========================================================================
    # Cache Operations
    # =========================================================================

    async def get(self, key: str) -> str | None:
        """Get a cached value by key."""
        return None

    async def set(self, key: str, value: str, ttl: int | None = 3600) -> None:
        """Set a cached value with optional TTL."""
        pass

    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        return True

    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        return False
