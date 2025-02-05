from typing import TypeVar, Generic, List

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class Paged(BaseModel, Generic[T]):
    count: int
    items: List[T]
