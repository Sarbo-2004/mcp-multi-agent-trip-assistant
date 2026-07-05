import json
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from services.hotel_service import HotelService


mcp = FastMCP(
    "hotel_mcp_server",
    host="127.0.0.1",
    port=8004,
    json_response=True,
)

hotel_service = HotelService()


@mcp.tool()
def search_hotels(
    destination: str,
    budget: Optional[str] = None,
    travelers: Optional[int] = None,
    limit: int = 10,
) -> str:
    result: Dict[str, Any] = hotel_service.search_hotels(
        destination=destination,
        budget=budget,
        travelers=travelers,
        limit=limit,
    )

    return json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")