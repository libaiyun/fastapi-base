import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import Column, DateTime, text, Index, Text, JSON
from sqlalchemy.dialects.mysql import TINYINT, BIGINT
from sqlmodel import SQLModel, Field, Relationship

from app.core.db import create_tables


class Team(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    headquarters: str

    heroes: list["Hero"] = Relationship(back_populates="team")


class Hero(SQLModel, table=True):
    __tablename__ = "hero"
    __table_args__ = (
        Index("hero_name_IDX", "name"),
        Index("hero_age_IDX", "age", "update_time"),
        {"comment": "英雄人物表"},
    )
    # `id` int(11) NOT NULL AUTO_INCREMENT,
    id: Optional[int] = Field(default=None, primary_key=True)
    # `parent_id` bigint(20) DEFAULT NULL,
    parent_id: Optional[int] = Field(default=None, sa_column=Column(BIGINT(20)))
    # `name` varchar(100) NOT NULL,
    name: str = Field(max_length=100)
    # `secret_name` varchar(255) NOT NULL,
    secret_name: str
    # `age` int(11) DEFAULT NULL,
    age: Optional[int] = None
    # `is_deprecated` tinyint(3) NOT NULL DEFAULT '0' COMMENT '是否弃用，0为否，1为是',
    is_deprecated: int = Field(
        default=0,
        sa_column=Column(TINYINT(3), nullable=False, server_default=text("'0'"), comment="是否弃用，0为否，1为是"),
    )
    # `intro` text NOT NULL,
    intro: str = Field(sa_column=Column(Text, nullable=False))
    # `pets` json DEFAULT NULL COMMENT '宠物列表',
    pets: Optional[List[str]] = Field(default=None, sa_column=Column(JSON, comment="宠物列表"))
    # `address_info` json NOT NULL COMMENT '地址信息',
    address_info: Dict[str, Any] = Field(sa_column=Column(JSON, nullable=False, comment="地址信息"))
    # `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    create_time: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), comment="创建时间"),
    )
    # `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    update_time: Optional[datetime] = Field(
        default=None,
        sa_column=Column(
            DateTime,
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            comment="更新时间",
        ),
    )

    team_id: Optional[int] = Field(default=None, foreign_key="team.id")
    # team_id: Optional[int] = None

    team: Optional[Team] = Relationship(back_populates="heroes")


if __name__ == "__main__":
    asyncio.run(create_tables())
