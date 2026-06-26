import logging
from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import ConnectionError, TimeoutError


logger = logging.getLogger(__name__)


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
    async def set(self, key: str, value: str, ex: int | None = 60) -> bool:
        try:
            return await self.client.set(key, value, ex=ex)

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
