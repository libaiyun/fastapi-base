import logging
from typing import Dict, Any

import jwt

from app.exceptions import AuthException, InvalidTokenError

logger = logging.getLogger(__name__)


def get_userinfo(authorization: str) -> Dict[str, Any]:
    if not authorization.startswith("Bearer "):
        raise AuthException("Authorization must be Bearer token")

    token = authorization[len("Bearer ") :]

    try:
        payload = jwt.decode(token, options={"verify_signature": False})  # 不验证签名，身份认证在网关层完成
    except (jwt.DecodeError, jwt.InvalidTokenError):
        logger.error("Invalid token: %s", token)
        raise InvalidTokenError

    return payload
