from datetime import datetime, timezone
from typing import Annotated

from pydantic import BeforeValidator


def ensure_timezone(value: datetime) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc).astimezone()
        else:
            return value.astimezone()
    return value


DateTime = Annotated[datetime, BeforeValidator(ensure_timezone)]
