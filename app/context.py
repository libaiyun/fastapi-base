import contextvars

request_id_context = contextvars.ContextVar("request_id", default=None)
user_id_context = contextvars.ContextVar("user_id", default=None)


def get_user_id() -> int | None:
    return user_id_context.get()
