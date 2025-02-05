from typing import TypeVar, Generic, Type, Dict, Any, List

from pydantic import BaseModel
from sqlalchemy.orm import load_only, selectinload
from sqlmodel import SQLModel, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.schemas.pagination import Paged
from app.schemas.query import CommonQuery, LogicCondition, Condition, SortOrder, ComplexQuery
from app.utils.condition_builder import ConditionBuilder
from app.utils.query_util import build_conditions, format_fields, format_sort, extract_query_params
from app.utils.string_util import split_comma_separated

T = TypeVar("T", bound=SQLModel)


class CRUDBase(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model

    async def create(self, session: AsyncSession, obj_new: BaseModel, extra_data: Dict[str, Any] = None) -> T:
        obj_db = self.model.model_validate(obj_new, update=extra_data)
        session.add(obj_db)
        await session.flush([obj_db])  # 执行SQL语句
        await session.refresh(obj_db)  # 从数据库刷新create_time和update_time
        return obj_db

    async def update(self, session: AsyncSession, obj_db: T, obj_new: Dict[str, Any] | BaseModel) -> T:
        if isinstance(obj_new, BaseModel):
            update_data = obj_new.model_dump(exclude_unset=True)
        else:
            update_data = obj_new
        obj_db.sqlmodel_update(update_data)
        session.add(obj_db)
        await session.flush([obj_db])
        await session.refresh(obj_db)  # 从数据库刷新update_time
        return obj_db

    async def list(
        self, session: AsyncSession, query: CommonQuery, condition: LogicCondition | Condition = None
    ) -> Paged[T]:
        query_params = extract_query_params(query)
        if query.count:
            count = await self.count(session, query_params, condition=condition)
        else:
            count = -1
        items = await self.get_list(
            session,
            query_params,
            condition=condition,
            fields=split_comma_separated(query.fields),
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            page=query.page,
            page_size=query.page_size,
        )
        return Paged[T](count=count, items=items)

    async def complex_query(self, session: AsyncSession, query: ComplexQuery) -> Paged[T]:
        if query.count:
            count = await self.count(session, condition=query.condition)
        else:
            count = -1
        items = await self.get_list(
            session,
            condition=query.condition,
            fields=query.fields,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            page=query.page,
            page_size=query.page_size,
        )
        return Paged[T](count=count, items=items)

    async def count(
        self, session: AsyncSession, query_params: Dict[str, Any] = None, condition: LogicCondition | Condition = None
    ) -> int:
        conditions = build_conditions(self.model, query_params)
        _condition = ConditionBuilder(self.model).build_condition(condition)
        if _condition is not None:
            conditions.append(_condition)
        result = await session.exec(select(func.count()).select_from(self.model).where(*conditions))
        return result.one()

    async def get_list(
        self,
        session: AsyncSession,
        query_params: Dict[str, Any] = None,
        condition: LogicCondition | Condition = None,
        fields: List[str] = None,
        sort_by: str = None,
        sort_order: SortOrder = SortOrder.ASC,
        page: int = 1,
        page_size: int = 100 * 10000,
    ) -> List[T]:
        conditions = build_conditions(self.model, query_params)
        _condition = ConditionBuilder(self.model).build_condition(condition)
        if _condition is not None:
            conditions.append(_condition)
        select_columns, relation_columns = format_fields(self.model, fields)
        sort_columns = format_sort(self.model, sort_by, sort_order)
        statement = select(self.model).where(*conditions).offset((page - 1) * page_size).limit(page_size)
        if select_columns:
            statement = statement.options(load_only(*select_columns, raiseload=True))
        if relation_columns:
            statement = statement.options(selectinload(*relation_columns))
        if sort_columns:
            statement = statement.order_by(*sort_columns)
        result = await session.exec(statement)
        return result.all()

    async def get_first(
        self,
        session: AsyncSession,
        query_params: Dict[str, Any] = None,
        condition: LogicCondition | Condition = None,
        fields: List[str] = None,
        sort_by: str = None,
        sort_order: SortOrder = SortOrder.ASC,
    ) -> T:
        items = await self.get_list(
            session,
            query_params,
            condition=condition,
            fields=fields,
            sort_by=sort_by,
            sort_order=sort_order,
            page=1,
            page_size=1,
        )
        return items[0] if items else None
