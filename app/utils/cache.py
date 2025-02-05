import time
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
