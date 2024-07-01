import redis.asyncio as redis_async  #type: ignore[import-untyped]
from src.configuration.settings import settings

redis_client_async = redis_async.Redis(host=settings.redis_host,
                        port=settings.redis_port,
                        db=0,
                        )
