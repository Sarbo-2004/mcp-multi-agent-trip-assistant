import uuid
from dataclasses import asdict, fields
from typing import Any, Dict, Optional

from langgraph.types import Command

from memory.redis_trip_memory import RedisTripMemory
from orchestrator.intent_analyzer import IntentAnalyzer
from orchestrator.state_manager import StateManager
from orchestrator.trip_graph import trip_graph
from schemas.trip_schema import TripRequest


class TripOrchestrator:
    """
    Public facade over the compiled trip-planning graph.

    app_mcp.py only calls run() on this class; it never touches LangGraph directly.

    Memory design:
    - Redis is used only at orchestrator level.
    - Agents do not directly read/write Redis.
    - Redis memory is loaded into TripState as trip_memory.
    - Current parsed request overrides Redis memory.
    - Redis memory fills missing fields for follow-up queries.
    """

    def __init__(self):
        self.graph = trip_graph
        self.intent_analyzer = IntentAnalyzer()
        self.state_manager = StateManager()
        self.memory_store = RedisTripMemory()

        self.thread_id = str(uuid.uuid4())
        self.last_completed_request: Optional[TripRequest] = None
        self.pending_clarification: Optional[Dict[str, Any]] = None

    def run(
        self,
        user_query: Optional[str] = None,
        answer: Any = None,
        debug: bool = False,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Advance the workflow by one turn.

        Pass user_query for a normal chat message.
        Pass answer for structured clarification replies.

        session_id is used for Redis short-term memory.
        """

        trip_memory = self.memory_store.load(session_id)

        if self._is_paused():
            resume_value = answer if answer is not None else user_query
            result = self._invoke(Command(resume=resume_value))
        else:
            result = self._start_new_plan(
                user_query=user_query or "",
                trip_memory=trip_memory,
            )

        response = self._build_response(result, debug=debug)

        self._persist_memory_if_needed(
            session_id=session_id,
            result=result,
            response=response,
            user_query=user_query,
            answer=answer,
        )

        return response

    # ------------------------------------------------------------------ #
    # Graph invocation
    # ------------------------------------------------------------------ #

    def _config(self) -> Dict[str, Any]:
        return {"configurable": {"thread_id": self.thread_id}}

    def _is_paused(self) -> bool:
        snapshot = self.graph.get_state(self._config())
        return bool(snapshot.next)

    def _sanitize_request_dict(self, request_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove fields not accepted by TripRequest.

        This prevents Redis memory keys like travel_style from breaking:
        TripRequest(**request_dict)
        """

        allowed_fields = {field.name for field in fields(TripRequest)}

        return {
            key: value
            for key, value in (request_dict or {}).items()
            if key in allowed_fields
        }

    def _start_new_plan(
        self,
        user_query: str,
        trip_memory: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Start a new planning turn.

        Steps:
        1. Parse current query.
        2. Apply existing in-process replan merge.
        3. Merge Redis memory into request.
        4. Sanitize request for TripRequest schema.
        5. Start LangGraph from a fresh thread.
        """

        self.thread_id = str(uuid.uuid4())
        self.pending_clarification = None

        parsed_request = self.intent_analyzer.analyze(user_query)

        if self.state_manager.is_replan_candidate(
            current_request=parsed_request,
            previous_request=self.last_completed_request,
        ):
            parsed_request = self.state_manager.merge_replan_request(
                previous_request=self.last_completed_request,
                current_request=parsed_request,
            )

        current_request_dict = self._sanitize_request_dict(asdict(parsed_request))

        merged_request_dict = self.memory_store.merge_memory_into_request(
            memory=trip_memory,
            current_request=current_request_dict,
        )

        merged_request_dict = self._sanitize_request_dict(merged_request_dict)

        initial_state = {
            "raw_user_query": user_query,
            "request": merged_request_dict,
            "trip_memory": trip_memory,
            "conversation_history": trip_memory.get("conversation_history", []),
        }

        return self._invoke(initial_state)

    def _invoke(self, payload: Any) -> Dict[str, Any]:
        result = self.graph.invoke(payload, self._config())
        interrupts = result.get("__interrupt__")

        # A node's writes just before interrupt() are not visible in result.
        # Clarification payload must be read from Interrupt.value.
        self.pending_clarification = interrupts[0].value if interrupts else None

        return result

    # ------------------------------------------------------------------ #
    # Memory persistence
    # ------------------------------------------------------------------ #

    def _persist_memory_if_needed(
        self,
        session_id: Optional[str],
        result: Dict[str, Any],
        response: Dict[str, Any],
        user_query: Optional[str],
        answer: Any,
    ) -> None:
        """
        Save Redis short-term memory only when a turn reaches a final response.

        Do not update final trip memory during clarification pause,
        because the graph state is not complete yet.
        """

        if not session_id:
            return

        if response.get("awaiting_clarification"):
            if user_query:
                self.memory_store.append_turn(
                    session_id=session_id,
                    role="user",
                    content=user_query,
                )
            return

        final_response_text = response.get("response")

        self.memory_store.update_from_state(
            session_id=session_id,
            state=result,
            final_response=final_response_text,
        )

        if user_query:
            self.memory_store.append_turn(
                session_id=session_id,
                role="user",
                content=user_query,
            )

        if answer is not None and not user_query:
            self.memory_store.append_turn(
                session_id=session_id,
                role="user",
                content=str(answer),
            )

        if final_response_text:
            self.memory_store.append_turn(
                session_id=session_id,
                role="assistant",
                content=final_response_text,
            )

    # ------------------------------------------------------------------ #
    # Response shaping
    # ------------------------------------------------------------------ #

    def _build_response(self, result: Dict[str, Any], debug: bool) -> Dict[str, Any]:
        if self.pending_clarification is not None:
            return self._build_clarification_response(debug=debug)

        return self._build_final_response(result, debug=debug)

    def _build_clarification_response(self, debug: bool) -> Dict[str, Any]:
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
        request = self._sanitize_request_dict(result.get("request") or {})
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
            "agent_results": result.get("agent_results", {}),
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

        return [
            name
            for name, agent_result in agent_results.items()
            if agent_result.get("success")
        ]

    def _failed_agents(self, result: Dict[str, Any]) -> list:
        agent_results = result.get("agent_results") or {}

        return [
            {
                "agent": name,
                "error": agent_result.get("error"),
            }
            for name, agent_result in agent_results.items()
            if not agent_result.get("success")
        ]