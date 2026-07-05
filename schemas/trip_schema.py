from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TypedDict


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


class TripState(TypedDict, total=False):
    """Shared trip-planning state — the single channel every agent reads and writes.

    This is the LangGraph graph state. It holds ONLY JSON-serializable values
    (dicts / lists / primitives) so it survives checkpointer serialization
    across an ``interrupt`` pause/resume. The rich dataclasses (``TripRequest``,
    ``AgentInput``, ``AgentOutput``) are reconstructed at node boundaries; they
    never live inside the state itself.
    """

    # --- Core planning inputs / outputs ---
    raw_user_query: str
    request: Dict[str, Any]                    # serialized TripRequest
    agent_results: Dict[str, Dict[str, Any]]   # agent_name -> serialized AgentOutput
    errors: List[str]
    conversation_history: List[Dict[str, Any]]

    # --- Planner-owned control fields (routing / phase bookkeeping) ---
    phase: str
    next_node: str
    pending_clarification: Optional[Dict[str, Any]]   # serialized ClarificationRequest
    clarification_answers: Dict[str, Any]
    asked_clarifications: List[str]            # rule ids already asked, prevents re-asking forever
    planned_agents: List[str]                  # agent set decided once destination is resolved

    # --- Hierarchical destination planning ---
    destination_resolved: bool
    selected_cities: List[str]
    city_recommendations: List[Dict[str, Any]]
    city_attractions: Dict[str, Any]                  # city -> ranked attractions

    # --- Transport / feasibility / replanning ---
    travel_sequence: Optional[Dict[str, Any]]
    feasible: Optional[bool]
    replan_count: int
    replan_directives: List[str]

    # --- Terminal ---
    final_response: Optional[Dict[str, Any]]
    done: bool


@dataclass
class FinalTripPlan:
    query: str
    destination: Optional[str]
    summary: str
    sections: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)