from enum import Enum
from typing import Optional, Any, List, Union, Type

from pydantic import BaseModel, conint, Field, create_model


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class Operator(str, Enum):
    EQ = "eq"
    NE = "ne"
    IN = "in"
    NOT_IN = "not_in"
    LT = "lt"
    GT = "gt"
    LE = "le"
    GE = "ge"
    JSON_CONTAINS = "json_contains"
    LIKE = "like"


class Pagination(BaseModel):
    page: conint(ge=1, le=1000) = Field(1, description="页码，范围为 1-1000")
    page_size: conint(ge=0, le=10 * 10000) = Field(10, description="每页返回的记录数，范围为 0-100000")


class Sort(BaseModel):
    sort_by: Optional[str] = Field(None, description="排序字段，支持任意字段名")
    sort_order: SortOrder = Field(SortOrder.ASC, description="排序方式，可选值：asc（升序）、desc（降序）")


class CommonQuery(Pagination, Sort, extra="forbid"):
    fields: str = Field(..., description="指定需要返回的字段，多个字段以英文逗号分隔")
    count: Optional[bool] = Field(False, description="是否返回总记录数")


class Condition(BaseModel):
    field: str = Field(..., description="查询条件的字段名称")
    operator: Operator = Field(Operator.EQ, description="操作符，用于指定条件的比较方式")
    value: Any = Field(..., description="查询条件的值")


class LogicCondition(BaseModel):
    and_: List[Union[Condition, "LogicCondition"]] | None = Field(None, description="多个条件的 AND 逻辑组合")
    or_: List[Union[Condition, "LogicCondition"]] | None = Field(None, description="多个条件的 OR 逻辑组合")


class ComplexQuery(Pagination, Sort, extra="forbid"):
    fields: List[str] = Field(..., description="指定需要返回的字段列表")
    count: Optional[bool] = Field(False, description="是否返回总记录数")
    condition: LogicCondition | Condition | None = Field(None, description="查询条件，可以是简单条件或复杂逻辑组合")


TEMP_QUERY_FIELDS = set()


def create_temp_query(query_class: Type[CommonQuery], **field_definitions: Any):
    model_name = "Temp" + query_class.__name__
    temp_query = create_model(model_name, **field_definitions, __base__=query_class)
    TEMP_QUERY_FIELDS.update(field_definitions)
    return temp_query
