import uuid
from dataclasses import asdict
from typing import Any, Dict, Optional

from langgraph.types import Command

from orchestrator.intent_analyzer import IntentAnalyzer
from orchestrator.state_manager import StateManager
from orchestrator.trip_graph import trip_graph
from schemas.trip_schema import TripRequest


class TripOrchestrator:
    """Public facade over the compiled trip-planning graph.

    ``app_mcp.py`` only ever calls ``run()`` on this class; it never touches
    LangGraph directly. A fresh ``thread_id`` is minted for every new user
    turn so each turn starts from a clean ``TripState`` (cross-turn carryover
    — e.g. "actually make it 5 days" — is handled explicitly via
    ``StateManager``, not by relying on checkpoint replay). The *same*
    ``thread_id`` is kept only across a clarification pause -> resume pair,
    since that is a single logical turn split across two calls.
    """

    def __init__(self):
        self.graph = trip_graph
        self.intent_analyzer = IntentAnalyzer()
        self.state_manager = StateManager()
        self.thread_id = str(uuid.uuid4())
        self.last_completed_request: Optional[TripRequest] = None
        self.pending_clarification: Optional[Dict[str, Any]] = None

    def run(
        self,
        user_query: Optional[str] = None,
        answer: Any = None,
        debug: bool = False,
    ) -> Dict[str, Any]:
        """Advance the workflow by one turn.

        Pass ``user_query`` for a normal chat message (new plan or free-text
        clarification reply). Pass ``answer`` when the caller already knows a
        clarification is pending and has a structured value to resume with
        (e.g. a button click or a multi-select list of city ids) — the UI
        decides the shape, ``PlannerAgent.merge_clarification_answer`` accepts
        both scalars and ``{question_id: value}`` dicts.
        """
        if self._is_paused():
            resume_value = answer if answer is not None else user_query
            result = self._invoke(Command(resume=resume_value))
        else:
            result = self._start_new_plan(user_query or "")

        return self._build_response(result, debug=debug)

    # ------------------------------------------------------------------ #
    # Graph invocation
    # ------------------------------------------------------------------ #

    def _config(self) -> Dict[str, Any]:
        return {"configurable": {"thread_id": self.thread_id}}

    def _is_paused(self) -> bool:
        snapshot = self.graph.get_state(self._config())
        return bool(snapshot.next)

    def _start_new_plan(self, user_query: str) -> Dict[str, Any]:
        self.thread_id = str(uuid.uuid4())

        parsed_request = self.intent_analyzer.analyze(user_query)

        if self.state_manager.is_replan_candidate(
            current_request=parsed_request,
            previous_request=self.last_completed_request,
        ):
            parsed_request = self.state_manager.merge_replan_request(
                previous_request=self.last_completed_request,
                current_request=parsed_request,
            )

        initial_state = {
            "raw_user_query": user_query,
            "request": asdict(parsed_request),
        }

        return self._invoke(initial_state)

    def _invoke(self, payload: Any) -> Dict[str, Any]:
        result = self.graph.invoke(payload, self._config())
        interrupts = result.get("__interrupt__")

        # A node's own writes just before it calls ``interrupt()`` are never
        # visible here or via ``get_state`` while paused — only the exact
        # payload passed into ``interrupt(...)`` is retrievable, via
        # ``Interrupt.value``. That is why the clarification questions are
        # read from here rather than from ``TripState["pending_clarification"]``.
        self.pending_clarification = interrupts[0].value if interrupts else None

        return result

    # ------------------------------------------------------------------ #
    # Response shaping
    # ------------------------------------------------------------------ #

    def _build_response(self, result: Dict[str, Any], debug: bool) -> Dict[str, Any]:
        if self.pending_clarification is not None:
            return self._build_clarification_response(debug=debug)

        return self._build_final_response(result, debug=debug)

    def _build_clarification_response(self, debug: bool) -> Dict[str, Any]:
        # Fields committed by nodes that ran before the pause (intake,
        # planner, any already-completed agents) ARE visible here.
        snapshot_values = self.graph.get_state(self._config()).values

        response = {
            "success": True,
            "awaiting_clarification": True,
            "clarification": self.pending_clarification,
            "request": snapshot_values.get("request"),
        }

        if debug:
            response["debug_state"] = snapshot_values

        return response

    def _build_final_response(self, result: Dict[str, Any], debug: bool) -> Dict[str, Any]:
        request = result.get("request") or {}
        final_response = result.get("final_response") or {}

        if result.get("done") and request:
            self.last_completed_request = TripRequest(**request)

        response = {
            "success": final_response.get("success", False),
            "response": final_response.get("response"),
            "error": final_response.get("error"),
            "awaiting_clarification": False,
            "request": {
                "source": request.get("source"),
                "destination": request.get("destination"),
                "month": request.get("month"),
                "days": request.get("days"),
                "budget": request.get("budget"),
                "travelers": request.get("travelers"),
                "interests": request.get("interests"),
                "parser_used": request.get("parser_used"),
                "turn_type": request.get("turn_type"),
                "modified_fields": request.get("modified_fields"),
            },
            "workflow": {
                "planned_agents": result.get("planned_agents", []),
                "completed_agents": self._completed_agents(result),
                "failed_agents": self._failed_agents(result),
                "replan_count": result.get("replan_count", 0),
                "replan_directives": result.get("replan_directives", []),
            },
            "summary": {
                "selected_cities": result.get("selected_cities", []),
                "city_recommendations": result.get("city_recommendations", []),
                "travel_sequence": result.get("travel_sequence"),
                "feasible": result.get("feasible"),
                "errors": result.get("errors", []),
            },
        }

        if debug:
            response["debug_state"] = result

        return response

    def _completed_agents(self, result: Dict[str, Any]) -> list:
        agent_results = result.get("agent_results") or {}
        return [name for name, agent_result in agent_results.items() if agent_result.get("success")]

    def _failed_agents(self, result: Dict[str, Any]) -> list:
        agent_results = result.get("agent_results") or {}
        return [
            {"agent": name, "error": agent_result.get("error")}
            for name, agent_result in agent_results.items()
            if not agent_result.get("success")
        ]
