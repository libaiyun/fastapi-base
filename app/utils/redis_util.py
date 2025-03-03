import aioredis

from app.exceptions import ConfigError
from config import config


def make_redis():
    if config.redis is None:
        raise ConfigError("Redis连接未配置")
    client = aioredis.from_url(
        config.redis.url,
        db=config.redis.db,
        decode_responses=True,  # 将响应自动解码为 Python 字符串
        max_connections=2**10,  # 最大连接数
        socket_timeout=3,  # socket 读写超时
        socket_connect_timeout=5,  # socket 建立连接超时
        retry_on_timeout=True,  # 超时自动重试
    )
    return client


redis_cli = make_redis()
