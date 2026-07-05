from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class MCPToolResponse:
    tool_name: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    raw_response: Optional[Any] = None
