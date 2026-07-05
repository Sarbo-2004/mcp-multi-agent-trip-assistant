from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Clarification "kind" values. Kept as module constants so the UI and planner
# agree on the vocabulary without magic strings scattered around.
KIND_FREE_TEXT = "free_text"
KIND_SINGLE_SELECT = "single_select"
KIND_MULTI_SELECT = "multi_select"


@dataclass
class ClarificationOption:
    """One selectable answer for a select-style question."""

    id: str
    label: str
    description: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClarificationQuestion:
    """A single question posed to the user.

    ``fills_field`` names the ``TripRequest`` field (or a well-known control
    field like ``selected_cities``) that the answer should populate. This lets
    the planner merge answers back generically without per-question code.
    """

    id: str
    question: str
    kind: str = KIND_FREE_TEXT
    options: List[ClarificationOption] = field(default_factory=list)
    fills_field: Optional[str] = None


@dataclass
class ClarificationRequest:
    """A pause-the-workflow request carrying one or more questions.

    Emitted from a node via ``interrupt(asdict(request))`` and rendered by the
    UI. Designed to be open-ended: new clarification types are added by
    appending a rule in the planner, never by changing the graph or this schema.
    """

    reason: str
    questions: List[ClarificationQuestion] = field(default_factory=list)
    origin: str = "clarify"          # which node raised it (clarify | city_selection)
