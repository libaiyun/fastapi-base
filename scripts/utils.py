import importlib
from typing import Mapping, Any


def render_callable(
    name: str,
    *args: object,
    kwargs: Mapping[str, object] | None = None,
    indentation: str = "",
) -> str:
    """
    Render a function call.

    :param name: name of the callable
    :param args: positional arguments
    :param kwargs: keyword arguments
    :param indentation: if given, each argument will be rendered on its own line with
        this value used as the indentation

    """
    if kwargs:
        args += tuple(f"{key}={value}" for key, value in kwargs.items())

    if indentation:
        prefix = f"\n{indentation}"
        suffix = "\n"
        delimiter = f",\n{indentation}"
    else:
        prefix = suffix = ""
        delimiter = ", "

    rendered_args = delimiter.join(str(arg) for arg in args)
    return f"{name}({prefix}{rendered_args}{suffix})"


def render_field(kwargs: dict[str, Any] = None) -> str | None:
    if not kwargs:
        return None
    if len(kwargs) == 1 and "default" in kwargs and kwargs["default"] is None:
        return None
    return render_callable("Field", kwargs=kwargs)


def get_table_comment(module_name, model_name) -> str:
    module = importlib.import_module(module_name)
    model = getattr(module, model_name)
    return model.__table__.comment
