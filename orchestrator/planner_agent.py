from typing import Any, Callable, Dict, List, Optional

from config.constants import (
    AGENT_DESTINATION,
    AGENT_BUDGET,
    NODE_CLARIFY,
    NODE_CITY_SELECTION,
    NODE_ATTRACTIONS,
    NODE_REPLAN,
    NODE_COMPOSE,
    PHASE_CLARIFY,
    PHASE_RESOLVE_DESTINATION,
    PHASE_SELECT_CITIES,
    PHASE_PLAN,
    PHASE_REPLAN,
    PHASE_COMPOSE,
    MAX_AUTO_REPLANS,
)
from schemas.clarification_schema import (
    ClarificationOption,
    ClarificationQuestion,
    ClarificationRequest,
    KIND_FREE_TEXT,
    KIND_MULTI_SELECT,
    KIND_SINGLE_SELECT,
)
from schemas.trip_schema import TripRequest, TripState
from orchestrator.workflow_planner import WorkflowPlanner


class ClarificationRule:
    """One extensible clarification case.

    ``applies(state)`` decides whether this case is currently relevant;
    ``build(state)`` produces the question to ask. Register new cases by
    appending a ``ClarificationRule`` to ``PlannerAgent.clarification_rules``
    — no other part of the workflow needs to change.
    """

    def __init__(
        self,
        rule_id: str,
        applies: Callable[[TripState], bool],
        build: Callable[[TripState], ClarificationQuestion],
    ):
        self.rule_id = rule_id
        self.applies = applies
        self.build = build


class PlannerAgent:
    """The single orchestrator brain.

    Every workflow decision — what to run next, whether clarification is
    needed, how to recover from an infeasible plan — is made here.
    LangGraph's nodes only carry out what this class decides; the graph's
    conditional edge just reads ``state["next_node"]``, a value this class
    computed.

    Agents never communicate with each other directly: everything this class
    reads comes from ``TripState``, and everything it decides is written
    back into ``TripState`` for the next node to read.
    """

    def __init__(self):
        self.workflow_planner = WorkflowPlanner()
        self.clarification_rules: List[ClarificationRule] = self._default_clarification_rules()

    # ------------------------------------------------------------------ #
    # Routing — the only place next-step workflow decisions are made
    # ------------------------------------------------------------------ #

    def decide_next(self, state: TripState) -> str:
        if not state.get("destination_resolved"):
            if self._destination_failed(state):
                return NODE_CLARIFY

            return AGENT_DESTINATION

        if state.get("city_recommendations") and not state.get("selected_cities"):
            return NODE_CITY_SELECTION

        if self._next_clarification_rule(state) is not None:
            return NODE_CLARIFY

        if self._missing_attraction_cities(state):
            return NODE_ATTRACTIONS

        # Only lock in the agent set once every clarification rule (including
        # ``missing_source_for_transport``) has already been resolved — doing
        # this any earlier would permanently exclude an agent (e.g. transport)
        # whose eligibility depends on a field the user hasn't supplied yet.
        self.ensure_planned_agents(state)

        planned_agents = state.get("planned_agents") or []
        agent_results = state.get("agent_results") or {}

        for agent_name in planned_agents:
            if agent_name == AGENT_DESTINATION:
                continue

            if agent_name not in agent_results:
                return agent_name

        if (
            state.get("feasible") is False
            and state.get("replan_count", 0) < MAX_AUTO_REPLANS
        ):
            return NODE_REPLAN

        return NODE_COMPOSE

    def phase_for_node(self, node_name: str) -> str:
        return {
            NODE_CLARIFY: PHASE_CLARIFY,
            NODE_CITY_SELECTION: PHASE_SELECT_CITIES,
            AGENT_DESTINATION: PHASE_RESOLVE_DESTINATION,
            NODE_REPLAN: PHASE_REPLAN,
            NODE_COMPOSE: PHASE_COMPOSE,
        }.get(node_name, PHASE_PLAN)

    def _destination_failed(self, state: TripState) -> bool:
        result = (state.get("agent_results") or {}).get(AGENT_DESTINATION)
        return bool(result and not result.get("success"))

    def _missing_attraction_cities(self, state: TripState) -> List[str]:
        selected_cities = state.get("selected_cities") or []
        city_attractions = state.get("city_attractions") or {}

        return [city for city in selected_cities if city not in city_attractions]

    # ------------------------------------------------------------------ #
    # Agent-set planning (invoked once, right after destination resolves)
    # ------------------------------------------------------------------ #

    def ensure_planned_agents(self, state: TripState) -> None:
        if state.get("planned_agents"):
            return

        request = self._request_from_state(state)
        state["planned_agents"] = self.workflow_planner.plan(request)

    # ------------------------------------------------------------------ #
    # Clarification — generic, rule-driven, extensible
    # ------------------------------------------------------------------ #

    def build_clarification(self, state: TripState) -> ClarificationRequest:
        rule = self._next_clarification_rule(state)

        if rule is None:
            return ClarificationRequest(
                reason="More information is needed before planning can continue.",
                questions=[
                    ClarificationQuestion(
                        id="general",
                        question="Could you share a bit more about what you're looking for in this trip?",
                        kind=KIND_FREE_TEXT,
                    )
                ],
                origin="clarify",
            )

        return ClarificationRequest(
            reason=f"Clarification needed: {rule.rule_id}",
            questions=[rule.build(state)],
            origin="clarify",
        )

    def build_city_selection(self, state: TripState) -> ClarificationRequest:
        recommendations = state.get("city_recommendations") or []

        options = [
            ClarificationOption(
                id=item.get("destination"),
                label=item.get("destination") or "Unknown",
                description=item.get("reason"),
                data=item,
            )
            for item in recommendations
            if item.get("destination")
        ]

        return ClarificationRequest(
            reason="Choose one or more destinations/cities to continue planning.",
            questions=[
                ClarificationQuestion(
                    id="select_cities",
                    question="Which of these would you like to visit?",
                    kind=KIND_MULTI_SELECT,
                    options=options,
                    fills_field=None,
                )
            ],
            origin="city_selection",
        )

    def merge_clarification_answer(
        self,
        state: TripState,
        clarification: ClarificationRequest,
        answer: Any,
    ) -> None:
        for question in clarification.questions:
            value = answer.get(question.id) if isinstance(answer, dict) else answer

            if clarification.origin == "city_selection" and question.id == "select_cities":
                cities = self._resolve_selected_cities(question, value)

                if cities:
                    state["selected_cities"] = cities

                continue

            coerced = self._coerce_answer(question, value)

            if question.fills_field:
                request = state.get("request") or {}
                request[question.fills_field] = coerced
                state["request"] = request
            else:
                self._apply_free_text_answer(state, coerced)

        asked = state.get("asked_clarifications") or []

        for question in clarification.questions:
            rule_id = question.id

            if rule_id not in asked:
                asked.append(rule_id)

        state["asked_clarifications"] = asked
        state["pending_clarification"] = None

    def _resolve_selected_cities(self, question: ClarificationQuestion, value: Any) -> List[str]:
        if isinstance(value, list):
            valid_ids = {option.id for option in question.options}
            cities = [item for item in value if item in valid_ids]

            if cities:
                return cities

        if isinstance(value, str) and value.strip():
            return self._match_options_from_text(value, question.options)

        return []

    def _match_options_from_text(self, text: str, options: List[ClarificationOption]) -> List[str]:
        lowered = text.lower()

        if lowered.strip() in {"all", "all of them", "both", "everything"}:
            return [option.id for option in options]

        matched = [
            option.id
            for option in options
            if option.label and option.label.lower() in lowered
        ]

        return matched

    def _coerce_answer(self, question: ClarificationQuestion, value: Any) -> Any:
        if value is None:
            return None

        if question.kind == KIND_MULTI_SELECT:
            if isinstance(value, list):
                return value

            return self._match_options_from_text(str(value), question.options)

        if question.kind == KIND_SINGLE_SELECT:
            if isinstance(value, str):
                for option in question.options:
                    if option.label.lower() == value.strip().lower() or option.id == value:
                        return option.id

            return value

        if question.fills_field == "days" or question.fills_field == "travelers":
            return self._safe_int(value)

        return value

    def _apply_free_text_answer(self, state: TripState, text: Any) -> None:
        if not text:
            return

        request = state.get("request") or {}
        combined_query = f"{request.get('user_query', '')}. {text}".strip(". ")
        request["user_query"] = combined_query
        state["request"] = request
        state["raw_user_query"] = combined_query

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        if isinstance(value, int):
            return value

        try:
            digits = "".join(char for char in str(value) if char.isdigit())
            return int(digits) if digits else None
        except (TypeError, ValueError):
            return None

    def _next_clarification_rule(self, state: TripState) -> Optional[ClarificationRule]:
        asked = set(state.get("asked_clarifications") or [])

        for rule in self.clarification_rules:
            if rule.rule_id in asked:
                continue

            if rule.applies(state):
                return rule

        return None

    def _default_clarification_rules(self) -> List[ClarificationRule]:
        def request_of(state: TripState) -> Dict[str, Any]:
            return state.get("request") or {}

        return [
            ClarificationRule(
                rule_id="missing_days",
                applies=lambda state: not request_of(state).get("days"),
                build=lambda state: ClarificationQuestion(
                    id="missing_days",
                    question="How many days do you have for this trip?",
                    kind=KIND_FREE_TEXT,
                    fills_field="days",
                ),
            ),
            ClarificationRule(
                rule_id="missing_budget",
                applies=lambda state: bool(state.get("destination_resolved")) and not request_of(state).get("budget"),
                build=lambda state: ClarificationQuestion(
                    id="missing_budget",
                    question="What budget range do you prefer?",
                    kind=KIND_SINGLE_SELECT,
                    options=[
                        ClarificationOption(id="low", label="low"),
                        ClarificationOption(id="medium", label="medium"),
                        ClarificationOption(id="high", label="high"),
                    ],
                    fills_field="budget",
                ),
            ),
            ClarificationRule(
                rule_id="missing_source_for_transport",
                applies=lambda state: (
                    len(state.get("selected_cities") or []) >= 1
                    and not request_of(state).get("source")
                ),
                build=lambda state: ClarificationQuestion(
                    id="missing_source_for_transport",
                    question="Which city will you be traveling from?",
                    kind=KIND_FREE_TEXT,
                    fills_field="source",
                ),
            ),
            ClarificationRule(
                rule_id="ambiguous_request",
                applies=lambda state: float(request_of(state).get("confidence") or 1.0) < 0.45,
                build=lambda state: ClarificationQuestion(
                    id="ambiguous_request",
                    question=(
                        "I want to get this right — could you tell me a bit more about your trip "
                        "(where from, roughly how long, and what you're looking for)?"
                    ),
                    kind=KIND_FREE_TEXT,
                    fills_field=None,
                ),
            ),
        ]

    # ------------------------------------------------------------------ #
    # Replanning
    # ------------------------------------------------------------------ #

    def apply_replan_directive(self, state: TripState) -> str:
        selected_cities = state.get("selected_cities") or []
        agent_results = dict(state.get("agent_results") or {})
        city_attractions = dict(state.get("city_attractions") or {})

        if len(selected_cities) > 1:
            directive = f"dropped_lowest_priority_city:{selected_cities[-1]}"
            dropped_city = selected_cities[-1]

            state["selected_cities"] = selected_cities[:-1]
            city_attractions.pop(dropped_city, None)
            state["city_attractions"] = city_attractions

            for agent_name in ("transport_agent", "itinerary_agent", "budget_agent"):
                agent_results.pop(agent_name, None)
        else:
            request = state.get("request") or {}
            current_days = request.get("days") or 3
            request["days"] = current_days + 2
            state["request"] = request
            directive = f"extended_days_to:{request['days']}"

            for agent_name in ("itinerary_agent", "budget_agent"):
                agent_results.pop(agent_name, None)

        state["agent_results"] = agent_results
        state["feasible"] = None
        state["replan_count"] = state.get("replan_count", 0) + 1

        directives = state.get("replan_directives") or []
        directives.append(directive)
        state["replan_directives"] = directives

        return directive

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _request_from_state(self, state: TripState) -> TripRequest:
        return TripRequest(**(state.get("request") or {"user_query": state.get("raw_user_query", "")}))
