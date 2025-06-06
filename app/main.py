import logging.config
from contextlib import asynccontextmanager

import aiohttp
import sentry_sdk
from fastapi import FastAPI, Depends
from fastapi.security import OAuth2PasswordRequestForm
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.api.deps.oauth2 import oauth2_scheme, get_signature
from app.core.log import LOGGING_CONFIG
from app.core.middleware import register_middlewares
from app.core.nacos.discovery import service_discovery
from app.exceptions import register_exception_handlers, RemoteServiceException
from app.core.make_api_offline import make_api_offline
from app.api.v1.router import router as api_v1
from app.schemas.error_report import ErrorReport
from app.schemas.token import Token
from app.config import config, APP_ENV
from app.core.nacos.config import ConfigSyncer
from app.utils.sw import start_sw_agent

logging.config.dictConfig(LOGGING_CONFIG)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with ConfigSyncer(config) as syncer:
        await syncer.start()

        try:
            await service_discovery.init()
            start_sw_agent()
            yield
        finally:
            await service_discovery.shutdown()


servers = None
dependencies = [
    Depends(get_signature),
]
if config.enable_oauth2:
    servers = [{"url": config.gateway.service_url, "description": "正式环境"}]
    dependencies.append(Depends(oauth2_scheme))
app = FastAPI(
    title="基于FastAPI的Python服务基础框架",
    description="基于FastAPI的Python服务基础框架，"
    "包含ORM、日志管理、任务调度、服务发现注册、统一配置管理、CI/CD、单元测试等通用设计。",
    version="1.0.0",
    servers=servers,
    dependencies=dependencies,
    lifespan=lifespan,
    root_path=f"/{config.service_name}",
)

make_api_offline(app)

register_middlewares(app)
register_exception_handlers(app)

if config.sentry.enabled:
    sentry_sdk.init(
        dsn=config.sentry.dsn,
        traces_sample_rate=config.sentry.traces_sample_rate,
        profiles_sample_rate=config.sentry.profiles_sample_rate,
        environment=APP_ENV,
    )

app.include_router(api_v1, prefix="/api/v1")


@app.get("/")
async def root():
    return {"code": 200, "message": "Hello World", "data": None}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if config.debug:

    @app.get("/config_info")
    async def get_config_info():
        return config.model_dump(mode="json")


if config.enable_oauth2:

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


if config.sentry.enabled:

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
            raise RemoteServiceException(f"Failed to report error: {str(e)}")
