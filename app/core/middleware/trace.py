import time
import uuid

from starlette.requests import Request

from app.context import request_id_context


async def add_request_id(request: Request, call_next):
    request_id = uuid.uuid4().hex
    request_id_context.set(request_id)
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


async def add_process_time(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(round(process_time * 1000))
    return response
