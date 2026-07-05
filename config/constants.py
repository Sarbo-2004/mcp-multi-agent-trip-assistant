AGENT_DESTINATION = "destination_agent"
AGENT_CLIMATE = "climate_agent"
AGENT_TRANSPORT = "transport_agent"
AGENT_HOTEL = "hotel_agent"
AGENT_ITINERARY = "itinerary_agent"
AGENT_BUDGET = "budget_agent"

# Canonical execution order. Every layer that selects or orders agents
# (intent analysis, workflow planning) must reuse this single list so the
# pipeline order can never drift between components.
AGENT_ORDER = [
    AGENT_DESTINATION,
    AGENT_CLIMATE,
    AGENT_TRANSPORT,
    AGENT_HOTEL,
    AGENT_ITINERARY,
    AGENT_BUDGET,
]

ALL_AGENTS = list(AGENT_ORDER)


# --- LangGraph node names ---
# Agent nodes reuse the AGENT_* ids above so a node maps 1:1 to an agent.
# These are the control/coordination nodes that surround them.
NODE_INTAKE = "intake"
NODE_PLANNER = "planner"
NODE_CLARIFY = "clarify"
NODE_CITY_SELECTION = "city_selection"
NODE_ATTRACTIONS = "attractions"
NODE_REPLAN = "replan"
NODE_COMPOSE = "compose"
NODE_END = "end"

# --- Planning phases (human-readable, stored in TripState["phase"]) ---
PHASE_INTAKE = "intake"
PHASE_CLARIFY = "clarify"
PHASE_RESOLVE_DESTINATION = "resolve_destination"
PHASE_SELECT_CITIES = "select_cities"
PHASE_PLAN = "plan"
PHASE_EVALUATE = "evaluate"
PHASE_REPLAN = "replan"
PHASE_COMPOSE = "compose"
PHASE_DONE = "done"

# --- Destination scope values ---
SCOPE_CITY = "city"
SCOPE_STATE = "state"
SCOPE_REGION = "region"
SCOPE_COUNTRY = "country"
SCOPE_UNKNOWN = "unknown"

# Scopes that must be narrowed to specific cities before detailed planning.
BROAD_SCOPES = {SCOPE_STATE, SCOPE_REGION, SCOPE_COUNTRY}

# Maximum number of automatic replanning iterations before the planner gives up
# and composes the best-effort plan it has.
MAX_AUTO_REPLANS = 3
