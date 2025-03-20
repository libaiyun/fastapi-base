from fastapi import FastAPI

from app.core.middleware.authenticate import authenticate_oauth2
from app.core.middleware.trace import add_request_id, add_process_time
from config import config


def register_middlewares(app: FastAPI):
    app.middleware("http")(add_request_id)
    app.middleware("http")(add_process_time)
    if config.enable_oauth2:
        app.middleware("http")(authenticate_oauth2)
