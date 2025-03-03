import logging

from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class ClientError(Exception):
    pass


class ServerException(Exception):
    pass


class OperationError(ClientError):
    pass


class RequestParamError(ClientError):
    pass


class ConfigError(ServerException):
    pass


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(ClientError)
    async def client_error_handler(request: Request, exc: "ClientError"):
        return JSONResponse(content={"code": 400, "message": str(exc)}, status_code=400)

    @app.exception_handler(ServerException)
    async def server_exception_handler(request: Request, exc: "ServerException"):
        return JSONResponse(content={"code": 500, "message": str(exc)}, status_code=500)

    @app.exception_handler(Exception)
    async def handle_exception(request: Request, exc: Exception):
        logger.exception(
            f"捕获未处理异常, 请求URL->{request.url}, request_id: {request.state.request_id}, 错误消息: {str(exc)}"
        )
        return JSONResponse(content={"code": 500, "message": str(exc)}, status_code=500)
