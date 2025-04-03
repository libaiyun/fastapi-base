from urllib.parse import urlparse

from aiocache import caches, SimpleMemoryCache, RedisCache

from app.config import config

redis_url = urlparse(config.redis.url)

caches.set_config(
    {
        "default": {
            "cache": "aiocache.SimpleMemoryCache",
            "serializer": {"class": "aiocache.serializers.PickleSerializer"},
        },
        "redis_alt": {
            "cache": "aiocache.RedisCache",
            "serializer": {"class": "aiocache.serializers.JsonSerializer"},
            "plugins": [{"class": "aiocache.plugins.HitMissRatioPlugin"}, {"class": "aiocache.plugins.TimingPlugin"}],
            "namespace": config.service_name,
            "timeout": 3,
            "endpoint": redis_url.hostname or "127.0.0.1",
            "port": redis_url.port or 6379,
            "db": config.redis.db,
            "password": redis_url.password or None,
        },
    }
)

mem_cache: SimpleMemoryCache = caches.get("default")
redis_cache: RedisCache = caches.get("redis_alt")
