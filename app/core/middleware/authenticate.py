import logging

from starlette.requests import Request
from starlette.responses import JSONResponse

from app.constants import AUTH_WHITELIST
from app.context import user_id_context, appid_context
from app.utils.auth_util import get_userinfo

logger = logging.getLogger(__name__)


async def set_authinfo(request: Request, call_next):
    appid = request.headers.get("cqvip-appid")
    if appid is not None:
        appid_context.set(appid)
    user_id = request.headers.get("user-id")
    if user_id is not None:
        user_id_context.set(user_id)

    response = await call_next(request)
    return response


async def authenticate(request: Request, call_next):
    if request.url.path in AUTH_WHITELIST:
        response = await call_next(request)
        return response

    authorization = request.headers.get("Authorization")
    if not authorization:
        return JSONResponse(content={"code": 401, "message": "Authorization header missing"}, status_code=401)

    try:
        user = get_userinfo(authorization=authorization)
        user_id_context.set(user["user_id"])
    except ValueError as e:
        logger.exception("Authentication error: %s" % str(e))
        return JSONResponse(content={"code": 401, "message": f"Authentication error: {str(e)}"}, status_code=401)
    except Exception as e:
        logger.exception("Unexpected authentication error: %s" % str(e))
        return JSONResponse(content={"code": 500, "message": "Unexpected authentication error"}, status_code=500)

    response = await call_next(request)
    return response
