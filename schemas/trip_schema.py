from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TripRequest:
    user_query: str
    source: Optional[str] = None
    destination: Optional[str] = None
    month: Optional[str] = None
    days: Optional[int] = None
    budget: Optional[str] = None
    travelers: Optional[int] = None
    interests: List[str] = field(default_factory=list)
    travel_dates: Optional[Dict[str, str]] = None

    suggested_agents: List[str] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    confidence: float = 0.0
    parser_used: str = "unknown"

    turn_type: str = "new_plan"
    modified_fields: List[str] = field(default_factory=list)
    clarification_questions: List[str] = field(default_factory=list)
    destination_scope: str = "unknown"


@dataclass
class TripContext:
    request: TripRequest
    extracted_entities: Dict[str, Any] = field(default_factory=dict)
    required_agents: List[str] = field(default_factory=list)
    agent_results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    pending_clarifications: List[str] = field(default_factory=list)
    last_user_action: Optional[str] = None


@dataclass
class FinalTripPlan:
    query: str
    destination: Optional[str]
    summary: str
    sections: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)