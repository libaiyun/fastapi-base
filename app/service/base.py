from typing import Type, TypeVar, Generic, Dict, Any, List

from pydantic import BaseModel
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.crud.base import CRUDBase
from app.exceptions import ResourceNotFound
from app.schemas.pagination import Paged
from app.schemas.query import CommonQuery, ComplexQuery
from app.utils.model_util import get_primary_keys, get_relationship_fields
from app.utils.string_util import split_comma_separated

T = TypeVar("T", bound=SQLModel)


class BaseService(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model
        self.crud = CRUDBase(model)

    async def create(self, session: AsyncSession, obj_new: BaseModel) -> T:
        db_item = await self.crud.create(session, obj_new)
        return db_item

    async def update(self, session: AsyncSession, pk: str, obj_new: BaseModel) -> T:
        primary_keys = get_primary_keys(self.model)
        if len(primary_keys) > 1:
            ident = tuple(pk.split(","))
        else:
            ident = pk
        db_item = await session.get(self.model, ident)
        if not db_item:
            raise ResourceNotFound("更新目标不存在")
        db_item = await self.do_update(session, db_item, obj_new)
        return db_item

    async def do_update(self, session: AsyncSession, db_item: T, obj_new: Dict[str, Any] | BaseModel) -> T:
        db_item = await self.crud.update(session, db_item, obj_new)
        return db_item

    async def list(self, session: AsyncSession, query: CommonQuery) -> Dict[str, Any]:
        data = await self.crud.list(session, query)
        return self._dump_paged_data(data, query.fields)

    async def complex_query(self, session: AsyncSession, query: ComplexQuery) -> Dict[str, Any]:
        data = await self.crud.complex_query(session, query)
        return self._dump_paged_data(data, query.fields)

    def _dump_paged_data(self, data: Paged, fields: List[str] | str):
        if isinstance(fields, str):
            _fields = split_comma_separated(fields)
        else:
            _fields = fields
        data_dict = data.model_dump()
        relation_fields = set(_fields) & set(get_relationship_fields(self.model))
        if not relation_fields:
            return data_dict
        # 序列化关系字段
        for item_obj, item_dict in zip(data.items, data_dict["items"]):
            for field_name in relation_fields:
                value = getattr(item_obj, field_name)
                if value is None:
                    item_dict[field_name] = None
                elif isinstance(value, BaseModel):
                    item_dict[field_name] = value.model_dump()
                elif isinstance(value, (list, set)):
                    item_dict[field_name] = [obj.model_dump() for obj in value]
                else:
                    item_dict[field_name] = str(value)  # 兜底处理，序列化为字符串
        return data_dict
