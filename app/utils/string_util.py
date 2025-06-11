from typing import List


def split_comma_separated(value: str, type_: type = str, separator: str = ",") -> List[str]:
    """将逗号分隔的字符串拆分成列表, 并转换元素为指定类型"""
    if not value:
        return []
    return [type_(i.strip()) for i in value.split(separator) if i.strip()]


def snake2pascal(snake_str: str) -> str:
    words = snake_str.split("_")
    return "".join(w.capitalize() for w in words)
