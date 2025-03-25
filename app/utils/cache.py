import asyncio
import hashlib
import inspect
import time
from collections import OrderedDict
from functools import lru_cache, wraps
from threading import Lock
from typing import Optional, Callable, Any


def timed_lru_cache(
    seconds: float,
    maxsize: Optional[int] = None,
    typed: bool = False,
    thread_safe: bool = True,
):
    """
    装饰器：为函数添加基于时间的LRU缓存。

    参数:
    - seconds: 缓存的有效时间（秒）
    - maxsize: 缓存的最大条目数，None表示无限制
    - typed: 是否区分参数类型（例如区分int和float）
    - thread_safe: 是否启用线程安全机制

    示例:
    >>> @timed_lru_cache(seconds=60)
    ... def expensive_function(x):
    ...     return x * x
    """

    def decorator(func: Callable) -> Callable:
        cache = lru_cache(maxsize=maxsize, typed=typed)(func)
        lock = Lock() if thread_safe else None
        last_clear_time = time.monotonic()  # 使用monotonic避免系统时间调整的影响

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal last_clear_time

            def _should_clear_cache() -> bool:
                return time.monotonic() - last_clear_time > seconds

            def _clear_if_needed() -> None:
                nonlocal last_clear_time
                if _should_clear_cache():
                    cache.cache_clear()
                    last_clear_time = time.monotonic()

            if thread_safe:
                with lock:  # type: ignore
                    _clear_if_needed()
                    result = cache(*args, **kwargs)
            else:
                _clear_if_needed()
                result = cache(*args, **kwargs)

            return result

        def cache_info():
            """返回缓存的当前状态和统计信息"""
            if thread_safe:
                with lock:  # type: ignore
                    return cache.cache_info()
            return cache.cache_info()

        def cache_clear():
            """手动清除缓存"""
            nonlocal last_clear_time
            if thread_safe:
                with lock:  # type: ignore
                    cache.cache_clear()
                    last_clear_time = time.monotonic()
            else:
                cache.cache_clear()
                last_clear_time = time.monotonic()

        def time_remaining() -> float:
            """返回距离下次缓存清理的剩余时间（秒）"""
            if thread_safe:
                with lock:  # type: ignore
                    return max(0.0, seconds - (time.monotonic() - last_clear_time))
            return max(0.0, seconds - (time.monotonic() - last_clear_time))

        # 绑定方法和属性到wrapper
        wrapper.cache_info = cache_info
        wrapper.cache_clear = cache_clear
        wrapper.time_remaining = time_remaining
        wrapper._cache = cache  # 用于测试和调试

        return wrapper

    return decorator


# 内存缓存存储结构（基于 LRU 淘汰策略）
class MemoryCache:
    def __init__(self, maxsize=1024):
        self._store = OrderedDict()
        self._lock = asyncio.Lock()  # 协程安全锁
        self.maxsize = maxsize
        self.hits = 0
        self.misses = 0

    async def get(self, key: str) -> Any:
        async with self._lock:
            entry = self._store.get(key)
            if entry:
                # 检查是否过期
                if entry["expire"] is None or entry["expire"] > time.monotonic():
                    self.hits += 1
                    self._store.move_to_end(key)
                    return entry["value"]
                else:
                    del self._store[key]  # 清理过期缓存
            self.misses += 1
            return None

    async def set(self, key: str, value: Any, expire_seconds: Optional[int]) -> None:
        async with self._lock:
            current_time = time.monotonic()
            # 清理所有过期条目
            expired_keys = [k for k, v in self._store.items() if v["expire"] and v["expire"] <= current_time]
            for k in expired_keys:
                del self._store[k]
            # 淘汰旧条目直到容量达标
            while len(self._store) >= self.maxsize:
                self._store.popitem(last=False)
            # 添加新条目
            expire = current_time + expire_seconds if expire_seconds else None
            self._store[key] = {"value": value, "expire": expire}
            self._store.move_to_end(key)

    async def mget(self, keys: list) -> dict:
        async with self._lock:
            return {key: await self.get(key) for key in keys}


# 全局缓存实例
cache = MemoryCache()


# TODO: 缓存方法时，不应该使用self的内存地址计算key
def cached(expire_seconds: Optional[int] = None) -> Callable:
    """内存缓存装饰器（支持同步/异步函数）"""

    def decorator(func: Callable) -> Callable:
        is_async = inspect.iscoroutinefunction(func)

        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            key = _generate_key(func, args, kwargs)
            cached_value = await cache.get(key)
            if cached_value is not None:
                return cached_value
            result = await func(*args, **kwargs)
            await cache.set(key, result, expire_seconds)
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            key = _generate_key(func, args, kwargs)
            # 同步函数需要特殊处理（示例简化版，实际建议异步优先）
            # 此处仅演示原理，生产环境建议统一使用异步
            cached_value = asyncio.run(cache.get(key))
            if cached_value is not None:
                return cached_value
            result = func(*args, **kwargs)
            asyncio.run(cache.set(key, result, expire_seconds))
            return result

        def _generate_key(_func: Callable, _args: tuple, _kwargs: dict) -> str:
            """生成唯一缓存键"""
            # 使用函数标识和参数生成哈希键
            key_data = (
                _func.__module__,
                _func.__name__,
                _args,
                frozenset(_kwargs.items()),
            )
            key_str = repr(key_data).encode()
            return hashlib.sha256(key_str).hexdigest()

        return async_wrapper if is_async else sync_wrapper

    return decorator
