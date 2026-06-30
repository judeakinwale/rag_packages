import logging
from uuid import uuid4

from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import ConnectionError, TimeoutError


logger = logging.getLogger(__name__)


RELEASE_LOCK_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
end
return 0
"""

REFRESH_LOCK_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("expire", KEYS[1], ARGV[2])
end
return 0
"""


class RedisClient:
    def __init__(self, host: str, port: int, password: str | None = None, db: int = 0):
        self.host = host
        self.port = port
        self.db = db
        self.pool = ConnectionPool(
            host=self.host,
            port=self.port,
            password=password,
            db=self.db,
            decode_responses=True,
        )
        self.client = Redis(connection_pool=self.pool)

    @staticmethod
    def generate_key(prefix: str, identifier: str) -> str:
        return f"{prefix}:{identifier}"

    def get_client(self) -> Redis:
        return self.client

    # ex is expiry in seconds
    async def set(
        self, key: str, value: str, ex: int | None = 60, nx: bool = False
    ) -> bool:
        try:
            return bool(await self.client.set(key, value, ex=ex, nx=nx))

        except (ConnectionError, TimeoutError):
            logger.exception(f"[RedisClient] Redis set failed for key '{key}':")
            return False

        except Exception:
            logger.exception(f"[RedisClient] Redis set failed for key '{key}':")
            raise

    async def get(self, key: str) -> str | None:
        try:
            return await self.client.get(key)

        except (ConnectionError, TimeoutError):
            logger.exception(f"[RedisClient] Redis get failed for key '{key}':")
            return None

        except Exception:
            logger.exception(f"[RedisClient] Redis get failed for key '{key}':")
            raise

    async def delete(self, key: str) -> bool:
        try:
            return await self.client.delete(key) > 0

        except (ConnectionError, TimeoutError):
            logger.exception(f"[RedisClient] Redis delete failed for key '{key}':")
            return False

        except Exception:
            logger.exception(f"[RedisClient] Redis delete failed for key '{key}':")
            raise

    async def acquire_lock(
        self, key: str, ttl_seconds: int, token: str | None = None
    ) -> str | None:
        """Acquire a Redis lock and return its ownership token when successful."""
        lock_token = token or uuid4().hex

        try:
            acquired = await self.client.set(
                key,
                lock_token,
                ex=ttl_seconds,
                nx=True,
            )
            return lock_token if acquired else None

        except (ConnectionError, TimeoutError):
            logger.exception(
                f"[RedisClient] Redis acquire lock failed for key '{key}':"
            )
            return None

        except Exception:
            logger.exception(
                f"[RedisClient] Redis acquire lock failed for key '{key}':"
            )
            raise

    async def release_lock(self, key: str, token: str) -> bool:
        """Release a Redis lock only if the caller still owns it."""
        try:
            return bool(await self.client.eval(RELEASE_LOCK_SCRIPT, 1, key, token))

        except (ConnectionError, TimeoutError):
            logger.exception(
                f"[RedisClient] Redis release lock failed for key '{key}':"
            )
            return False

        except Exception:
            logger.exception(
                f"[RedisClient] Redis release lock failed for key '{key}':"
            )
            raise

    async def refresh_lock(self, key: str, token: str, ttl_seconds: int) -> bool:
        """Extend a Redis lock TTL only if the caller still owns it."""
        try:
            return bool(
                await self.client.eval(
                    REFRESH_LOCK_SCRIPT,
                    1,
                    key,
                    token,
                    ttl_seconds,
                )
            )

        except (ConnectionError, TimeoutError):
            logger.exception(
                f"[RedisClient] Redis refresh lock failed for key '{key}':"
            )
            return False

        except Exception:
            logger.exception(
                f"[RedisClient] Redis refresh lock failed for key '{key}':"
            )
            raise

    async def close(self):
        await self.client.close()
        await self.pool.disconnect()

    async def ping(self) -> bool:
        try:
            return await self.client.ping()

        except (ConnectionError, TimeoutError):
            logger.exception("[RedisClient] Redis ping failed:")
            return False

        except Exception:
            logger.exception("[RedisClient] Redis ping failed:")
            raise
