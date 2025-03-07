from app.utils.redis_util import redis_cli
from config import APP_ENV


# 示例: _=Depends(partial(api_lock, lock_key="update_hero")),
async def api_lock(lock_key: str, timeout: int = 60):
    lock_key = f"{APP_ENV}_lock:{lock_key}"
    async with redis_cli.lock(lock_key, timeout=timeout):
        yield
