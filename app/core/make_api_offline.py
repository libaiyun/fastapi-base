from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html, get_redoc_html
from starlette.responses import HTMLResponse
from starlette.staticfiles import StaticFiles


def remove_route(app: FastAPI, url: str) -> None:
    """
    remove original route from app
    """
    index = None
    for i, r in enumerate(app.routes):
        if r.path.lower() == url.lower():
            index = i
            break
    if isinstance(index, int):
        app.routes.pop(index)


def make_api_offline(
    app: FastAPI,
    static_dir=Path(__file__).parent.parent.parent / "static",
    static_url="/static-offline-docs",
    docs_url: Optional[str] = "/docs",
    redoc_url: Optional[str] = "/redoc",
) -> None:
    openapi_url = app.openapi_url  # /openapi.json
    swagger_ui_oauth2_redirect_url = app.swagger_ui_oauth2_redirect_url  # /docs/oauth2-redirect
    # 静态文件挂载
    app.mount(
        static_url,
        StaticFiles(directory=Path(static_dir).as_posix()),
        # as_posix 它用于将路径对象转换为字符串，并使用 POSIX（Portable Operating System Interface）风格的路径分隔符（即斜杠 /）
        name="static-offline-docs",
    )

    if docs_url is not None:
        remove_route(app, docs_url)
        remove_route(app, swagger_ui_oauth2_redirect_url)

        @app.get(docs_url, include_in_schema=False)
        async def custom_swagger_ui_html(request: Request) -> HTMLResponse:
            root = request.scope.get("root_path")
            favicon = f"{root}{static_url}/favicon.png"
            return get_swagger_ui_html(
                openapi_url=f"{root}{openapi_url}",
                title=app.title + " - Swagger UI",
                oauth2_redirect_url=swagger_ui_oauth2_redirect_url,
                swagger_js_url=f"{root}{static_url}/swagger-ui-bundle.js",
                swagger_css_url=f"{root}{static_url}/swagger-ui.css",
                swagger_favicon_url=favicon,
            )

        @app.get(swagger_ui_oauth2_redirect_url, include_in_schema=False)
        async def swagger_ui_redirect() -> HTMLResponse:
            return get_swagger_ui_oauth2_redirect_html()

    if redoc_url is not None:
        remove_route(app, redoc_url)

        @app.get(redoc_url, include_in_schema=False)
        async def redoc_html(request: Request) -> HTMLResponse:
            root = request.scope.get("root_path")
            favicon = f"{root}{static_url}/favicon.png"

            return get_redoc_html(
                openapi_url=f"{root}{openapi_url}",
                title=app.title + " - ReDoc",
                redoc_js_url=f"{root}{static_url}/redoc.standalone.js",
                with_google_fonts=False,
                redoc_favicon_url=favicon,
            )
