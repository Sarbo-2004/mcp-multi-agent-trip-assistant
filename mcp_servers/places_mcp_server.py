import json
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from services.places_service import PlacesService


mcp = FastMCP(
    "places_mcp_server",
    host="127.0.0.1",
    port=8001,
    json_response=True,
)

places_service = PlacesService()


@mcp.tool()
def recommend_destinations(
    source: Optional[str] = None,
    interests: Optional[List[str]] = None,
    month: Optional[str] = None,
    budget: Optional[str] = None,
    days: Optional[int] = None,
    travelers: Optional[int] = None,
    limit: int = 8,
) -> str:
    result: Dict[str, Any] = places_service.recommend_destinations(
        source=source,
        interests=interests or [],
        month=month,
        budget=budget,
        days=days,
        travelers=travelers,
        limit=limit,
    )

    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def get_popular_places(
    destination: str,
    interests: Optional[List[str]] = None,
    limit: int = 10,
) -> str:
    result: Dict[str, Any] = places_service.get_popular_places(
        destination=destination,
        interests=interests or [],
        limit=limit,
    )

    return json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")