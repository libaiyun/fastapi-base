import os

from app.utils.string_util import snake2pascal
from scripts.utils import get_table_comment

API_TEMPLATE = """\
from app.api.router_base import RouterBase, Route
from app.models.{module_name} import {model_name}
from app.schemas.{module_name} import {model_name}Query, {model_name}Create, {model_name}Update, {model_name}Public

router = RouterBase({model_name}, {model_name}Query, {model_name}Create, {model_name}Update, {model_name}Public).get_router({include_routes})
"""

ROUTER_TEMPLATE = """\
from fastapi import APIRouter

from app.api.v1.routes import (
{routes}
)

router = APIRouter()

{include_router}
"""


def generate_apis(write=False):
    routes = []
    include_router = []
    for filename in os.listdir("../app/models"):
        if not filename.endswith(".py") or filename == "__init__.py":
            continue

        module_name = filename[:-3]
        model_name = snake2pascal(module_name)

        if module_name == "dict_manual_edit_entity":
            include_routes = "include_routes={RouteType.LIST}"
        else:
            include_routes = ""

        api_content = API_TEMPLATE.format(module_name=module_name, model_name=model_name, include_routes=include_routes)
        if write:
            with open(os.path.join("../app/api/v1/routes", filename), "w", encoding="utf-8") as f:
                f.write(api_content)
        else:
            print(api_content)

        routes.append(f"    {module_name}")

        table_comment = get_table_comment(f"app.models.{module_name}", model_name)
        include_router.append(
            f'router.include_router({module_name}.router, prefix="/{module_name}", tags=["{table_comment}({module_name})"])'
        )

    router_content = ROUTER_TEMPLATE.format(
        routes=", \n".join(routes),
        include_router="\n".join(include_router),
    )

    if write:
        with open("../app/api/v1/router.py", "w", encoding="utf-8") as f:
            f.write(router_content)
    else:
        print(router_content)


if __name__ == "__main__":
    generate_apis(True)
