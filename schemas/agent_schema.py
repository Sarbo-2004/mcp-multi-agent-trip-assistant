from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class AgentInput:
    query: str
    source: Optional[str] = None
    destination: Optional[str] = None
    month: Optional[str] = None
    days: Optional[int] = None
    budget: Optional[str] = None
    travelers: Optional[int] = None
    interests: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentOutput:
    agent_name: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    message: Optional[str] = None
    error: Optional[str] = None


@dataclass
class AgentMetadata:
    name: str
    description: str
    depends_on: List[str] = field(default_factory=list)
    output_key: Optional[str] = None