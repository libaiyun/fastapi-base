from typing import Optional

from fastapi import Header
from fastapi.security import OAuth2PasswordBearer

from config import config

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"http://{config.host}:{config.port}/token", auto_error=False)


async def get_signature(
    authorization: Optional[str] = Header(None),
):
    """OpenAPI全局请求头声明"""
