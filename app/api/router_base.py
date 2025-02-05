from enum import Enum
from typing import Type, Annotated, Set, Dict

from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_session
from app.schemas.pagination import Paged
from app.schemas.query import CommonQuery, ComplexQuery
from app.schemas.response import APIResponse
from app.service.base import BaseService
from app.utils.model_util import get_primary_keys


class Route(str, Enum):
    LIST = "list"
    CREATE = "create"
    UPDATE = "update"


class RouterBase:
    def __init__(
        self,
        model: Type[SQLModel],
        schema_query: Type[CommonQuery],
        schema_create: Type[BaseModel],
        schema_update: Type[BaseModel],
        schema_response: Type[BaseModel],
        service_class: Type[BaseService] = BaseService,
    ):
        self.model = model
        self.schema_query = schema_query
        self.schema_create = schema_create
        self.schema_update = schema_update
        self.schema_response = schema_response
        self.service: BaseService = service_class(self.model)

    def get_router(self, routes: Set[Route] = None, update_doc: Dict[str, str] = None):
        if routes is None:
            routes = set(Route)

        router = APIRouter()
        if Route.LIST in routes:
            self._add_list_routes(router)
        if Route.CREATE in routes:
            self._add_create_route(router)
        if Route.UPDATE in routes:
            self._add_update_route(router)

        self.update_route_doc(router, update_doc)
        return router

    @staticmethod
    def update_route_doc(router: APIRouter, update_doc: Dict[str, str]):
        if not update_doc:
            return
        for route in router.routes:
            doc = update_doc.get(route.name)
            if doc:
                route.description = doc

    def _add_list_routes(self, router: APIRouter):
        schema_query = self.schema_query
        route_kwargs = {
            "response_model": APIResponse[Paged[self.schema_response]],
            "response_model_exclude_unset": True,
        }

        @router.get("/list", **route_kwargs, summary=f"{self.model.__name__} 列表查询")
        async def read_items(query: Annotated[schema_query, Query()], session: AsyncSession = Depends(get_session)):
            """列表查询

            **查询参数**:

            - `page`: 页码，默认1
            - `page_size`: 每页数据条数，默认10
            - `sort_by`: 排序字段，如sort_by=keyid
            - `sort_order`: 排序顺序，"asc"表示升序，"desc"表示降序，默认升序
            - `fields`: 查询和返回的字段，英文逗号分隔的字段名列表，如fields=ref_id,order
            - `count`: 是否查询返回总记录数，true/false，默认false

            **字段筛选参数**:

            - `xx`: 字段等值查询，如sub_db_id=00854
            - `xx__le`: 字段`xx`小于等于指定值
            - `xx__ge`: 字段`xx`大于等于指定值
            - `xx__in`: 字段`xx`的多值查询，多个值以英文逗号分隔
            - `xx__not_in`: 字段`xx`的否定多值查询，多个值以英文逗号分隔
            - `xx__json_contains`: json数组字段的包含查询

            **示例**

            - 查询第1页，每页20条数据，按照`keyid`升序排序:
              `/list?page=1&page_size=20&sort_by=keyid&sort_order=asc`
            - 查询返回`ref_id`和`lngid`字段:
              `/list?fields=ref_id,lngid`
            - 查询创建时间在2024-09-03的数据:
              `/list?create_time__ge=2024-09-03 00:00:00&create_time__le=2024-09-03 23:59:59`
            - 查询`source_type`字段为3或4的数据：
              `list/?source_type__in=3,4`"""
            data = await self.service.list(session, query)
            return APIResponse(data=data)

        @router.post("/list", **route_kwargs, summary=f"{self.model.__name__} 列表查询")
        async def post_read_items(query: schema_query, session: AsyncSession = Depends(get_session)):
            """POST类型的列表查询，参数与GET xx/list一致。用请求体参数代替查询参数，解决参数长度限制问题。"""
            data = await self.service.list(session, query)
            return APIResponse(data=data)

        @router.post("/query", **route_kwargs, summary=f"{self.model.__name__} 复杂条件查询")
        async def complex_query(query: ComplexQuery, session: AsyncSession = Depends(get_session)):
            """复杂条件查询接口

            在 `condition` 字段以 JSON 组合条件，基本条件格式为：

            `{"field": "","operator": "eq", "value": ""}`

            以 `and_` 或者 `or_` 包裹多个基本条件，组成逻辑条件：

            `{"and_": [{"field": "","operator": "eq", "value": ""}, ...]}`

            `{"or_": [{"field": "","operator": "eq", "value": ""}, ...]}`

            `and_` 或者 `or_` 可以继续包含逻辑条件形成嵌套：

            `{"and_": [{"field": "","operator": "eq", "value": ""}, "or_": [...]]}`

            `operator` 的枚举如下：

            - `eq`: 等于
            - `ne`: 不等于
            - `in`: 在列表中
            - `not_in`: 不在列表中
            - `lt`: 小于
            - `gt`: 大于
            - `le`: 小于等于
            - `ge`: 大于等于
            - `json_contains`: json数组字段的包含查询
            - `like`: 字符串模糊匹配

            `value` 多值的以 json 数组表示，如：

            `{"field": "sex", "operator": "in", "value": [0, 1]}`

            示例：

            ```json
            {
              "sort_by": null,
              "sort_order": "asc",
              "page": 1,
              "page_size": 10,
              "fields": ["author_id", "author", "organ"],
              "count": false,
              "condition": {
                "and_": null,
                "or_": [
                  {
                    "field": "author",
                    "operator": "like",
                    "value": "浩景"
                  },
                  {
                    "field": "organ",
                    "operator": "eq",
                    "value": "常州纺织服装职业技术学院"
                  },
                  {
                    "and_": null,
                    "or_": null
                  }
                ]
              }
            }
            ```"""
            data = await self.service.complex_query(session, query)
            return APIResponse(data=data)

    def _add_create_route(self, router: APIRouter):
        schema_create = self.schema_create

        @router.post("/create", response_model=APIResponse[self.schema_response], summary=f"{self.model.__name__} 创建")
        async def create_item(item: schema_create, session: AsyncSession = Depends(get_session)):
            db_item = await self.service.create(session, item)
            return APIResponse(data=db_item)

    def _add_update_route(self, router: APIRouter):
        schema_update = self.schema_update

        @router.post(
            "/update/{pk}",
            response_model=APIResponse[self.schema_response],
            summary=f"{self.model.__name__} 更新",
            description="更新接口\n\n路径参数`pk`表示主键`{pk}`，即更新`{pk}`=pk的记录，联合主键多个值以`,`分隔".format(
                pk=",".join(get_primary_keys(self.model))
            ),
        )
        async def update_item(pk: str, item: schema_update, session: AsyncSession = Depends(get_session)):
            db_item = await self.service.update(session, pk, item)
            return APIResponse(data=db_item)
