from typing import Optional

from fastapi import Header
from fastapi.security import OAuth2PasswordBearer

from config import config

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"http://{config.server.host}:{config.server.port}/token", auto_error=False
)


async def get_signature(
    cqvip_appid: Optional[str] = Header(None),
    cqvip_ts: Optional[str] = Header(None),
    cqvip_sign: Optional[str] = Header(None),
    cqvip_type: Optional[str] = Header(None),
    sign_path: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
    user_id: Optional[str] = Header(None),
):
    """OpenAPI全局请求头声明"""
