from fastapi.security import OAuth2PasswordBearer

from app.core.db import session_factory
from app.utils.redis_util import redis_cli
from config import config


async def get_session():
    async with session_factory() as session:
        yield session
        await session.commit()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"http://{config.host}:{config.port}/token", auto_error=False)


# 示例: _=Depends(partial(api_lock, lock_key="update_hero")),
async def api_lock(lock_key: str, timeout: int = 60):
    lock_key = f"{config.environment}_lock:{lock_key}"
    async with redis_cli.lock(lock_key, timeout=timeout):
        yield
