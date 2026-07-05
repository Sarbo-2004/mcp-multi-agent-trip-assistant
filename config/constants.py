AGENT_DESTINATION = "destination_agent"
AGENT_CLIMATE = "climate_agent"
AGENT_TRANSPORT = "transport_agent"
AGENT_HOTEL = "hotel_agent"
AGENT_ITINERARY = "itinerary_agent"
AGENT_BUDGET = "budget_agent"

ALL_AGENTS = [
    AGENT_DESTINATION,
    AGENT_CLIMATE,
    AGENT_TRANSPORT,
    AGENT_HOTEL,
    AGENT_ITINERARY,
    AGENT_BUDGET,
]

MCP_SERVER_PLACES = "places_mcp_server"
MCP_SERVER_CLIMATE = "climate_mcp_server"
MCP_SERVER_TRANSPORT = "transport_mcp_server"
MCP_SERVER_HOTEL = "hotel_mcp_server"

DEFAULT_TIMEOUT = 30

MONTHS = [
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
]

INTEREST_KEYWORDS = {
    "beach": ["beach", "beaches", "sea", "coast", "coastal"],
    "nature": ["nature", "forest", "wildlife", "hills", "mountains", "waterfall", "lake"],
    "religious": ["temple", "church", "mosque", "spiritual", "pilgrimage", "religious"],
    "adventure": ["adventure", "trek", "trekking", "rafting", "sports", "scuba"],
    "heritage": ["heritage", "history", "historical", "fort", "palace", "museum"],
    "nightlife": ["nightlife", "clubs", "party", "pub", "bar"],
    "food": ["food", "cuisine", "street food", "restaurants", "local food"],
    "shopping": ["shopping", "market", "markets", "souvenirs"],
}

BUDGET_KEYWORDS = {
    "low": ["low budget", "cheap", "budget", "affordable", "economy"],
    "medium": ["medium budget", "moderate", "standard"],
    "high": ["luxury", "premium", "expensive", "high budget"],
}