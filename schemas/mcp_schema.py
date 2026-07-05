from dataclasses import dataclass, field
from typing import Dict, Optional, Any


@dataclass
class MCPToolRequest:
    tool_name: str
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPToolResponse:
    tool_name: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    raw_response: Optional[Any] = None


@dataclass
class MCPServerConfig:
    name: str
    base_url: str
    transport: str = "http"
    timeout: int = 30