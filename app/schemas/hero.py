from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field

from app.models.hero import Team
from app.schemas.query import CommonQuery


class HeroQuery(CommonQuery):
    fields: str = "id,name"
    id: Optional[int] = None
    parent_id: Optional[int] = None
    name: Optional[str] = Field(default=None, max_length=100)
    secret_name: Optional[str] = None
    age: Optional[int] = None
    is_deprecated: Optional[int] = Field(default=None, description="是否弃用，0为否，1为是")
    intro: Optional[str] = None
    pets__json_contains: Optional[str] = Field(default=None, description="宠物列表包含?")
    create_time__le: Optional[datetime] = Field(default=None, description="创建时间<=?")
    create_time__ge: Optional[datetime] = Field(default=None, description="创建时间>=?")
    update_time__le: Optional[datetime] = Field(default=None, description="更新时间>=?")
    update_time__ge: Optional[datetime] = Field(default=None, description="更新时间>=?")
    team_id: Optional[int] = None


class HeroCreate(BaseModel):
    parent_id: Optional[int] = None
    name: str = Field(max_length=100)
    secret_name: str
    age: Optional[int] = None
    is_deprecated: int = Field(default=0, description="是否弃用，0为否，1为是")
    intro: str
    pets: Optional[List[str]] = Field(default=None, description="宠物列表")
    address_info: Dict[str, Any] = Field(default=None, description="地址信息")
    team_id: Optional[int] = None


class HeroBase(BaseModel):
    parent_id: Optional[int] = None
    name: Optional[str] = Field(max_length=100)
    secret_name: Optional[str] = None
    age: Optional[int] = None
    is_deprecated: Optional[int] = Field(default=None, description="是否弃用，0为否，1为是")
    intro: Optional[str] = None
    pets: Optional[List[str]] = Field(default=None, description="宠物列表")
    address_info: Optional[Dict[str, Any]] = Field(default=None, description="地址信息")
    team_id: Optional[int] = None


class HeroUpdate(HeroBase):
    pass


class HeroPublic(HeroBase):
    id: Optional[int] = None
    create_time: Optional[datetime] = Field(default=None, description="创建时间")
    update_time: Optional[datetime] = Field(default=None, description="更新时间")
    team: Optional[Team] = None
