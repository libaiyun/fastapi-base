from typing import Optional, Dict, Any
from pydantic import BaseModel


class ErrorReport(BaseModel):
    error_type: str
    error_message: str
    stack_trace: Optional[str] = None
    user_id: Optional[str] = None
    device_info: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
