import os
import re
from typing import Type, Any

from sqlalchemy import inspect, JSON, String
from sqlmodel import SQLModel
import importlib

from scripts.utils import render_field

SCHEMA_TEMPLATE = """
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any, ClassVar

from pydantic import BaseModel, Field, ConfigDict

from app.schemas.query import CommonQuery


class {model_name}Query(CommonQuery):
{query_fields}

{leftmost_index_fields}


class {model_name}Create(BaseModel):
{create_fields}


class {model_name}Base(BaseModel):
{model_config}
{base_fields}


class {model_name}Update({model_name}Base):
{update_fields}


class {model_name}Public({model_name}Base):
{public_fields}
"""


def get_python_type_name(column) -> str:
    try:
        python_type = column.type.python_type
    except NotImplementedError:
        return "Any"
    comment = column.comment
    if isinstance(column.type, JSON) and isinstance(comment, str) and "json数组" in comment.lower():
        return "list"
    return python_type.__name__


def sanitize_description(desc: str) -> str:
    """清理描述文本，处理换行和多余空格"""
    if not desc:
        return desc
    # 替换换行符
    desc = desc.replace("\r", " ").replace("\n", " ")
    # 压缩连续空格
    desc = re.sub(r"\s+", " ", desc)
    return desc


def get_field_def(field_name, python_type_name, kwargs) -> str:
    # 特别处理list类型，添加examples参数
    if python_type_name.lower() in ("list", "optional[list]") and "examples" not in kwargs:
        kwargs["examples"] = ["[]"]
    default = render_field(kwargs=kwargs)
    if default is None and "Optional" not in python_type_name:
        return f"    {field_name}: {python_type_name}"
    return f"    {field_name}: {python_type_name} = {render_field(kwargs=kwargs)}"


def get_optional_field_def(field_name, python_type_name, kwargs) -> str:
    # 特别处理list类型，添加examples参数
    if python_type_name.lower() in ("list", "optional[list]") and "examples" not in kwargs:
        kwargs["examples"] = ["[]"]
    if "Optional" not in python_type_name:
        python_type_name = f"Optional[{python_type_name}]"
    return get_field_def(field_name, python_type_name, {"default": None, **kwargs})


def get_time_field_defs(field_name, python_type_name, kwargs):
    return (
        get_optional_field_def(field_name + "__le", python_type_name, kwargs),
        get_optional_field_def(field_name + "__ge", python_type_name, kwargs),
    )


def generate_schema(model: Type[SQLModel]) -> str:
    assert issubclass(model, SQLModel)

    query_fields, create_fields, update_fields, public_fields = [], [], [], []
    model_config = ""
    indexed_column_names = set()
    primary_key_names = list(map(lambda c: c.name, model.__table__.primary_key))

    leftmost_index_column_names = list(primary_key_names)
    for index in model.__table__.indexes:
        for column in index.columns:
            indexed_column_names.add(column.name)
        first_column = next(iter(index.columns))
        leftmost_index_column_names.append(first_column.name)
    leftmost_index_column_names.sort()

    return_fields = []

    for column in inspect(model).columns.values():
        python_type_name = get_python_type_name(column)
        field_name = column.name
        kwargs: dict[str, Any] = {}

        if (
            (column.autoincrement is True and column.name in column.table.primary_key)
            or column.nullable
            or column.server_default
        ):
            kwargs["default"] = None
            python_type_name = f"Optional[{python_type_name}]"

        if field_name.startswith("_"):
            kwargs["alias"] = f'"{field_name}"'
            field_name = field_name[1:]
            model_config = "    model_config = ConfigDict(populate_by_name=True)"

        # 修复描述中的双引号问题
        if column.comment:
            # 清理描述文本
            description = sanitize_description(column.comment)
            # 使用JSON转义并确保使用单引号
            description = description.replace('"', '\\"')  # 转义双引号
            kwargs["description"] = f'"{description}"'  # 用双引号包裹整个字符串

        if isinstance(column.type, String) and column.type.length is not None:
            kwargs["max_length"] = column.type.length

        if field_name not in ("create_time", "update_time"):
            create_fields.append(get_field_def(field_name, python_type_name, kwargs))
            if not column.primary_key:
                update_fields.append(get_optional_field_def(field_name, python_type_name, kwargs))

        if field_name in indexed_column_names or column.primary_key:
            if "datetime" in python_type_name:
                query_fields.extend(get_time_field_defs(field_name, python_type_name, kwargs))
            else:
                query_fields.append(get_optional_field_def(field_name, python_type_name, kwargs))
            return_fields.append(field_name)

        public_fields.append(get_optional_field_def(field_name, python_type_name, kwargs))

    common_fields = set(update_fields) & set(public_fields)
    base_fields = [i for i in update_fields if i in common_fields]
    update_fields = [i for i in update_fields if i not in common_fields]
    public_fields = [i for i in public_fields if i not in common_fields]

    if return_fields:
        return_fields_str = ",".join(return_fields)
        query_fields.insert(
            0,
            f'    fields: str = Field("{return_fields_str}", description="指定需要返回的字段，多个字段以英文逗号分隔")',
        )

    schema_content = SCHEMA_TEMPLATE.format(
        model_name=model.__name__,
        model_config=model_config,
        base_fields="\n".join(base_fields),
        query_fields="\n".join(query_fields),
        create_fields="\n".join(create_fields),
        update_fields="\n".join(update_fields) or "    pass",
        public_fields="\n".join(public_fields),
        # leftmost_index_fields=f"    LEFTMOST_INDEX_FIELDS: ClassVar[list[str]] = {leftmost_index_column_names}",
        leftmost_index_fields="",
    )
    return schema_content


def generate_schemas(output_dir: str = None):
    pattern = re.compile("(?!^)([A-Z]+)")
    for filename in os.listdir("../app/models"):
        if (not filename.endswith(".py")) or filename == "__init__.py":
            continue

        module_name = filename[:-3]
        module = importlib.import_module(f"app.models.{module_name}")
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if not isinstance(attr, type) or not issubclass(attr, SQLModel) or attr is SQLModel:
                continue

            schema_content = generate_schema(model=attr)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                filename = re.sub(pattern, r"_\1", attr_name).lower() + ".py"
                with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
                    f.write(schema_content)
            else:
                print(schema_content)


if __name__ == "__main__":
    generate_schemas("../app/schemas")
