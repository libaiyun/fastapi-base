import logging
import traceback
from typing import Any

from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppException(Exception):
    ERROR_CODE = "00000"
    MESSAGE = "APP异常"
    STATUS_CODE = 500
    LOG_LEVEL = logging.ERROR

    def __init__(self, message: str = None, data: Any = None, *args):
        """
        :param message: 错误消息
        :param data: 错误数据
        :param args: 其他参数
        """
        super(AppException, self).__init__(*args)
        self.message = self.MESSAGE if message is None else message
        self.data = data

    def render_data(self):
        return self.data

    @property
    def response_data(self):
        return {
            "code": self.ERROR_CODE,
            "message": self.message,
            "data": self.render_data(),
        }

    def __str__(self):
        parts = [f"[{self.ERROR_CODE}] {self.message}", f"(Status: {self.STATUS_CODE})"]
        if self.data is not None:
            parts.append(f"Data: {self.data}")
        return " ".join(parts)

    def __repr__(self):
        return f"{self.__class__.__name__}(" f"message={self.message!r}, " f"data={self.data!r})"


class ClientException(AppException):
    ERROR_CODE = "40000"
    MESSAGE = "客户端请求异常"
    STATUS_CODE = 400
    LOG_LEVEL = logging.INFO


class ServerException(AppException):
    ERROR_CODE = "50000"
    MESSAGE = "服务端服务异常"
    STATUS_CODE = 500


# ------------------------- 客户端异常 (4xxxx) -------------------------
class ParamException(ClientException):
    """参数异常基类"""

    ERROR_CODE = "40010"
    MESSAGE = "请求参数异常"


class ParamValidationError(ParamException):
    ERROR_CODE = "40011"
    MESSAGE = "参数校验失败"


class ParamRequired(ParamException):
    ERROR_CODE = "40012"
    MESSAGE = "关键参数缺失"


class AuthException(ClientException):
    """认证异常基类"""

    ERROR_CODE = "40020"
    MESSAGE = "身份认证异常"
    STATUS_CODE = 401


class InvalidTokenError(AuthException):
    ERROR_CODE = "40021"
    MESSAGE = "无效的访问令牌"


class JwtVerifyError(AuthException):
    ERROR_CODE = "40022"
    MESSAGE = "JWT校验失败"


class PermissionException(ClientException):
    """权限异常基类"""

    ERROR_CODE = "40030"
    MESSAGE = "权限不足"
    STATUS_CODE = 403


class OperationForbidden(PermissionException):
    ERROR_CODE = "40031"
    MESSAGE = "操作不允许"


class AccessForbidden(PermissionException):
    ERROR_CODE = "40032"
    MESSAGE = "登录失败"


class RequestForbidden(PermissionException):
    ERROR_CODE = "40033"
    MESSAGE = "请求拒绝"


class ResourceLock(PermissionException):
    ERROR_CODE = "40034"
    MESSAGE = "资源被锁定"


class ResourceNotFound(ClientException):
    ERROR_CODE = "40040"
    MESSAGE = "找不到请求的资源"
    STATUS_CODE = 404


class MethodError(ClientException):
    ERROR_CODE = "40050"
    MESSAGE = "请求方法不支持"
    STATUS_CODE = 405


# ------------------------- 服务端异常 (5xxxx) -------------------------
class DatabaseError(ServerException):
    ERROR_CODE = "50010"
    MESSAGE = "数据库异常"


class RemoteServiceException(ServerException):
    """远程服务异常基类"""

    ERROR_CODE = "50020"
    MESSAGE = "远程服务异常"
    STATUS_CODE = 503


class ApiNetworkError(RemoteServiceException):
    ERROR_CODE = "50021"
    MESSAGE = "远程服务网络异常"


class ApiResultError(RemoteServiceException):
    ERROR_CODE = "50022"
    MESSAGE = "远程服务返回结果异常"


class ApiNotAcceptable(RemoteServiceException):
    ERROR_CODE = "50023"
    MESSAGE = "远程服务数据格式异常"


class StateTransitionError(ServerException):
    ERROR_CODE = "50030"
    MESSAGE = "状态流转异常"


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        logger.log(
            exc.LOG_LEVEL,
            "捕获主动抛出异常: [%s], 具体异常堆栈->[%s]"
            % (
                str(exc),
                traceback.format_exc(),
            ),
        )
        return JSONResponse(content=exc.response_data, status_code=exc.STATUS_CODE)

    @app.exception_handler(Exception)
    async def handle_exception(request: Request, exc: Exception):
        request_params = {
            "path_params": request.path_params,
            "query_params": request.query_params,
        }
        logger.error(
            "捕获未处理异常: [%s], 请求链ID->[%s] 请求URL->[%s], 请求方法->[%s] 请求参数->[%s] 异常具体堆栈->[%s]"
            % (
                str(exc),
                request.state.request_id,
                request.url.path,
                request.method,
                request_params,
                traceback.format_exc(),
            )
        )
        return JSONResponse(
            content={"code": "50000", "message": f"系统异常, 请联系管理员处理: {exc}", "data": None}, status_code=500
        )
