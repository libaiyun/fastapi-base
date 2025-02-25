import logging.config

import aiohttp
import sentry_sdk
from fastapi import FastAPI, Depends
from fastapi.security import OAuth2PasswordRequestForm
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.api.deps import oauth2_scheme, get_signature
from app.core.log import LOGGING_CONFIG
from app.core.middleware import register_middlewares
from app.exceptions import register_exception_handlers, ServerException
from app.core.make_api_offline import make_api_offline
from app.api.v1.router import router as api_v1
from app.schemas.error_report import ErrorReport
from app.schemas.token import Token
from config import config

logging.config.dictConfig(LOGGING_CONFIG)

logger = logging.getLogger(__name__)

app = FastAPI(
    servers=[
        {"url": config.gateway.service_url, "description": "Production environment"},
    ]
    if config.enable_auth
    else None,
    dependencies=[Depends(oauth2_scheme), Depends(get_signature)] if config.enable_auth else None,
)

make_api_offline(app)

register_middlewares(app)
register_exception_handlers(app)

if config.sentry.enabled:
    sentry_sdk.init(
        dsn=config.sentry.dsn,
        traces_sample_rate=config.sentry.traces_sample_rate,
        profiles_sample_rate=config.sentry.profiles_sample_rate,
        environment=config.environment,
    )

app.include_router(api_v1, prefix="/api/v1")


@app.get("/")
async def root():
    return {"code": 200, "message": "Hello World", "data": None}


@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    params = {
        "username": form_data.username,
        "password": form_data.password,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(config.gateway.login_url, json=params) as response:
            result = await response.json()
    access_token = result["data"]["access_token"]
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/errors/report")
async def report_error(error_report: ErrorReport, request: Request):
    """
    接收客户端的错误报告并发送到 Sentry
    """
    try:
        # 构建额外的上下文信息
        extra_context = {
            "request_url": str(request.url),
            "request_headers": dict(request.headers),
            "device_info": error_report.device_info,
            "metadata": error_report.metadata,
        }

        # 发送到 Sentry
        with sentry_sdk.new_scope() as scope:
            # 设置额外信息
            scope.set_extra("error_context", extra_context)

            # 设置用户信息
            if error_report.user_id:
                scope.set_user({"id": error_report.user_id})

            # 捕获异常
            sentry_sdk.capture_message(
                f"{error_report.error_type}: {error_report.error_message}",
                "error",
                extras={"stack_trace": error_report.stack_trace},
            )

        return JSONResponse(content={"message": "Error reported successfully"}, status_code=200)

    except Exception as e:
        logger.exception("Error while reporting to Sentry")
        raise ServerException(f"Failed to report error: {str(e)}")
