import copy
import json
import uuid
from typing import Any, Dict, Optional

import redis

from config.settings import redis_settings


DEFAULT_TRIP_MEMORY = {
    "request_memory": {
        "source": None,
        "destination": None,
        "days": None,
        "month": None,
        "budget": None,
        "travelers": None,
        "interests": [],
    },
    "planning_memory": {
        "selected_cities": [],
        "dropped_cities": [],
        "replan_count": 0,
        "last_feasible": None,
    },
    "response_memory": {
        "last_final_response": None,
        "last_summary": None,
    },
    "conversation_history": [],
}


class RedisTripMemory:
    """
    Redis-backed short-term trip memory.

    Redis is only used by app/orchestrator layer.
    Agents should not directly read/write Redis.
    """

    def __init__(self):
        self.enabled = redis_settings.redis_enabled
        self.redis_url = redis_settings.redis_url
        self.ttl_seconds = redis_settings.redis_ttl_seconds
        self.namespace = redis_settings.redis_namespace
        self.client = None

        if not self.enabled:
            print("[RedisTripMemory] Disabled by settings.")
            return

        if not self.redis_url:
            print("[RedisTripMemory] REDIS_URL missing. Memory disabled.")
            self.enabled = False
            return

        try:
            self.client = redis.Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=redis_settings.redis_socket_timeout,
                socket_connect_timeout=redis_settings.redis_socket_connect_timeout,
                protocol=2,
            )
            self.client.ping()
            print("[RedisTripMemory] Connected to Redis successfully.")
        except Exception as e:
            print("[RedisTripMemory] Redis unavailable. Memory disabled.")
            print(type(e).__name__, str(e))
            self.client = None
            self.enabled = False

    def create_session_id(self) -> str:
        return str(uuid.uuid4())

    def default_memory(self) -> Dict[str, Any]:
        return copy.deepcopy(DEFAULT_TRIP_MEMORY)

    def _key(self, session_id: str) -> str:
        return f"{self.namespace}:{session_id}"

    def load(self, session_id: Optional[str]) -> Dict[str, Any]:
        if not session_id:
            return self.default_memory()

        if not self.enabled or not self.client:
            return self.default_memory()

        raw = self.client.get(self._key(session_id))

        if not raw:
            return self.default_memory()

        try:
            return self._normalize_memory(json.loads(raw))
        except Exception:
            return self.default_memory()

    def save(self, session_id: Optional[str], memory: Dict[str, Any]) -> None:
        if not session_id:
            return

        if not self.enabled or not self.client:
            return

        normalized = self._normalize_memory(memory)

        self.client.setex(
            self._key(session_id),
            self.ttl_seconds,
            json.dumps(normalized, ensure_ascii=False),
        )

    def clear(self, session_id: Optional[str]) -> None:
        if not session_id:
            return

        if not self.enabled or not self.client:
            return

        self.client.delete(self._key(session_id))

    def append_turn(
        self,
        session_id: Optional[str],
        role: str,
        content: str,
        max_turns: int = 8,
    ) -> Dict[str, Any]:
        memory = self.load(session_id)

        history = memory.get("conversation_history") or []
        history.append(
            {
                "role": role,
                "content": content,
            }
        )

        memory["conversation_history"] = history[-max_turns:]
        self.save(session_id, memory)

        return memory

    def merge_memory_into_request(
        self,
        memory: Dict[str, Any],
        current_request: Dict[str, Any],
    ) -> Dict[str, Any]:
        request_memory = memory.get("request_memory") or {}
        merged = copy.deepcopy(request_memory)

        for key, value in (current_request or {}).items():
            if self._is_meaningful(value):
                merged[key] = value

        return merged

    def update_from_state(
        self,
        session_id: Optional[str],
        state: Dict[str, Any],
        final_response: Optional[str] = None,
    ) -> Dict[str, Any]:
        memory = self.load(session_id)

        request = state.get("request") or {}

        memory["request_memory"] = self._merge_request_memory(
            old_memory=memory.get("request_memory") or {},
            current_request=request,
        )

        memory["planning_memory"] = {
            "selected_cities": state.get("selected_cities") or [],
            "dropped_cities": self._extract_dropped_cities(state),
            "replan_count": state.get("replan_count", 0),
            "last_feasible": state.get("feasible"),
        }

        memory["response_memory"] = {
            "last_final_response": final_response or state.get("final_response"),
            "last_summary": {
                "selected_cities": state.get("selected_cities") or [],
                "feasible": state.get("feasible"),
                "travel_sequence": state.get("travel_sequence"),
            },
        }

        self.save(session_id, memory)
        return memory

    def _merge_request_memory(
        self,
        old_memory: Dict[str, Any],
        current_request: Dict[str, Any],
    ) -> Dict[str, Any]:
        merged = copy.deepcopy(old_memory or {})

        fields = [
            "source",
            "destination",
            "days",
            "month",
            "budget",
            "travelers",
            "interests",
        ]

        for field in fields:
            if field not in current_request:
                continue

            value = current_request.get(field)

            if self._is_meaningful(value):
                merged[field] = value

        return merged

    def _normalize_memory(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        default = self.default_memory()

        if not isinstance(memory, dict):
            return default

        for key, value in default.items():
            if key not in memory:
                memory[key] = copy.deepcopy(value)

        request_memory = memory.get("request_memory") or {}

        # Remove old unsupported keys saved in Redis, such as travel_style.
        allowed_request_fields = set(default["request_memory"].keys())
        request_memory = {
            key: value
            for key, value in request_memory.items()
            if key in allowed_request_fields
        }

        memory["request_memory"] = {
            **default["request_memory"],
            **request_memory,
        }

        memory["planning_memory"] = {
            **default["planning_memory"],
            **(memory.get("planning_memory") or {}),
        }

        memory["response_memory"] = {
            **default["response_memory"],
            **(memory.get("response_memory") or {}),
        }

        if not isinstance(memory.get("conversation_history"), list):
            memory["conversation_history"] = []

        memory["conversation_history"] = memory["conversation_history"][-8:]

        return memory

    def _extract_dropped_cities(self, state: Dict[str, Any]):
        directives = state.get("replan_directives") or []
        dropped = []

        for directive in directives:
            if not isinstance(directive, dict):
                continue

            city = directive.get("drop_city") or directive.get("city")

            if city:
                dropped.append(city)

        return dropped

    def _is_meaningful(self, value: Any) -> bool:
        if value is None:
            return False

        if isinstance(value, str) and not value.strip():
            return False

        if isinstance(value, list) and len(value) == 0:
            return False

        if isinstance(value, dict) and len(value) == 0:
            return False

        return True