import re
from typing import Type, Dict, Any, List, Tuple

from sqlalchemy import ColumnElement
from sqlalchemy.orm import Relationship
from sqlmodel import SQLModel, func

from app.exceptions import RequestParamError
from app.schemas.query import CommonQuery, TEMP_QUERY_FIELDS, SortOrder
from app.utils.string_util import split_comma_separated

PATTERN = re.compile(r"^(?P<field>\w+)__(?P<op>in|not_in|lt|gt|le|ge|json_contains)$")


def extract_query_params(query: CommonQuery):
    return query.model_dump(exclude_none=True, exclude=set(CommonQuery.model_fields) | TEMP_QUERY_FIELDS)


def build_conditions(model: Type[SQLModel], query_params: Dict[str, Any] = None) -> List[ColumnElement[bool]]:
    if not query_params:
        return []
    conditions = []
    for field, value in query_params.items():
        if hasattr(model, field):
            conditions.append(getattr(model, field) == value)
            continue
        match = PATTERN.match(field)
        if not match:
            raise RequestParamError(f"字段不存在或不支持的查询条件: {field}")
        field_name = match.group("field")
        op = match.group("op")
        if not hasattr(model, field_name):
            raise RequestParamError(f"字段不存在: {field}")
        field_attr = getattr(model, field_name)
        match op:
            case "in":
                if isinstance(value, str):
                    value = split_comma_separated(value)
                if len(value) == 1:
                    # tidb in 单值可能查不到
                    conditions.append(field_attr == value[0])
                else:
                    conditions.append(field_attr.in_(value))
            case "not_in":
                if isinstance(value, str):
                    value = split_comma_separated(value)
                conditions.append(~field_attr.in_(value))
            case "lt":
                conditions.append(field_attr < value)
            case "gt":
                conditions.append(field_attr > value)
            case "le":
                conditions.append(field_attr <= value)
            case "ge":
                conditions.append(field_attr >= value)
            case "json_contains":
                conditions.append(func.json_contains(field_attr, f'"{value}"'))
    return conditions


def format_sort(model: Type[SQLModel], sort_by: str, sort_order: SortOrder) -> list:
    """格式化排序条件"""
    if not sort_by:
        return []
    sort_columns = []
    sort_fields = split_comma_separated(sort_by)
    for field in sort_fields:
        column = getattr(model, field, None)
        if not column:
            raise ValueError(f"Invalid sort_by field: {field}")
        if sort_order is SortOrder.DESC:
            column = column.desc()
        sort_columns.append(column)
    return sort_columns


def format_fields(model: Type[SQLModel], fields: List[str] | str) -> Tuple[list, list]:
    if not fields:
        return [], []
    if isinstance(fields, str):
        fields = map(lambda f: f.strip(), fields.split(","))
    select_columns = []
    relation_columns = []
    for field in fields:
        if hasattr(model, field):
            field_attr = getattr(model, field)
            if isinstance(field_attr.property, Relationship):
                relation_columns.append(field_attr)
            else:
                select_columns.append(field_attr)
    return select_columns, relation_columns
