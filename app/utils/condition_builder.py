from typing import Type, List, Union, Optional

from sqlalchemy import ColumnElement
from sqlmodel import SQLModel, func, and_, or_

from app.exceptions import RequestParamError
from app.schemas.query import Condition, Operator, LogicCondition


class ConditionBuilder:
    def __init__(self, model: Type[SQLModel]):
        self.model = model

    def build_single_condition(self, cond: Condition):
        if not hasattr(self.model, cond.field):
            raise RequestParamError(f"查询条件中的字段 `{cond.field}` 不存在")
        field_attr = getattr(self.model, cond.field)
        match cond.operator:
            case Operator.EQ:
                return field_attr == cond.value
            case Operator.NE:
                return field_attr != cond.value
            case Operator.IN:
                return field_attr.in_(cond.value)
            case Operator.NOT_IN:
                return ~field_attr.in_(cond.value)
            case Operator.LT:
                return field_attr < cond.value
            case Operator.GT:
                return field_attr > cond.value
            case Operator.LE:
                return field_attr <= cond.value
            case Operator.GE:
                return field_attr >= cond.value
            case Operator.JSON_CONTAINS:
                return func.json_contains(field_attr, f'"{cond.value}"')
            case Operator.LIKE:
                return field_attr.like(f"%{cond.value}%")

    def process_conditions(
            self, conditions: List[Union[Condition, LogicCondition]], expr
    ) -> Optional[ColumnElement[bool]]:
        clauses = []
        for sub_cond in conditions:
            if isinstance(sub_cond, LogicCondition):
                if (clause := self.build_condition(sub_cond)) is not None:
                    clauses.append(clause)
            elif isinstance(sub_cond, Condition):
                clauses.append(self.build_single_condition(sub_cond))
        if clauses:
            return expr(*clauses)

    def build_condition(self, cond: LogicCondition | Condition) -> Optional[ColumnElement[bool]]:
        if cond is None:
            return None
        if isinstance(cond, Condition):
            return self.build_single_condition(cond)
        outer_clauses = []
        if cond.and_:
            outer_clauses.append(self.process_conditions(cond.and_, expr=and_))
        if cond.or_:
            outer_clauses.append(self.process_conditions(cond.or_, expr=or_))
        if valid_clauses := list(filter(lambda x: x is not None, outer_clauses)):
            return and_(*valid_clauses)
