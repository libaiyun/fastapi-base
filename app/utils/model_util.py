from typing import Type, List

from pydantic import BaseModel
from sqlalchemy.orm import Mapper, RelationshipProperty
from sqlmodel import SQLModel, inspect


def get_primary_key(model: Type[SQLModel]) -> str:
    mapper: Mapper = inspect(model).mapper
    return next(iter(mapper.primary_key)).name


def get_primary_keys(model: Type[SQLModel]):
    mapper: Mapper = inspect(model).mapper
    return [column.name for column in mapper.primary_key]


def get_relationship_fields(model: SQLModel) -> List[str]:
    relationship_fields = []
    for field_name, field in model.__mapper__.relationships.items():
        if isinstance(field, RelationshipProperty):
            relationship_fields.append(field_name)
    return relationship_fields


def model_dump(instance: BaseModel, fields: List[str] | str) -> str:
    pass
