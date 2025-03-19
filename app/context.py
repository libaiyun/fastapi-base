import contextvars

request_id_context = contextvars.ContextVar("request_id", default=None)
user_id_context = contextvars.ContextVar("user_id", default="")
appid_context = contextvars.ContextVar("appid", default="")


def get_user_id() -> str:
    return user_id_context.get()


def get_appid() -> str:
    return appid_context.get()
