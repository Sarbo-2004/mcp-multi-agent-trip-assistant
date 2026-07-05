from typing import Any, Dict, List, Optional

from config.settings import mcp_settings
from mcp_clients.base_mcp_client import BaseMCPClient
from schemas.mcp_schema import MCPToolResponse


class PlacesMCPClient(BaseMCPClient):
    def __init__(self):
        super().__init__(
            server_url=mcp_settings.places_mcp_url,
            server_name="places_mcp_server",
        )

    def get_popular_places(
        self,
        destination: str,
        interests: Optional[List[str]] = None,
        limit: int = 10,
    ) -> MCPToolResponse:
        return self.call_tool(
            tool_name="get_popular_places",
            arguments={
                "destination": destination,
                "interests": interests or [],
                "limit": limit,
            },
        )

    def recommend_destinations(
        self,
        source: Optional[str] = None,
        interests: Optional[List[str]] = None,
        month: Optional[str] = None,
        budget: Optional[str] = None,
        days: Optional[int] = None,
        travelers: Optional[int] = None,
        limit: int = 8,
    ) -> MCPToolResponse:
        return self.call_tool(
            tool_name="recommend_destinations",
            arguments={
                "source": source,
                "interests": interests or [],
                "month": month,
                "budget": budget,
                "days": days,
                "travelers": travelers,
                "limit": limit,
            },
        )

    def classify_destination(self, name: str) -> MCPToolResponse:
        return self.call_tool(
            tool_name="classify_destination",
            arguments={"name": name},
        )

    def recommend_cities_in_region(
        self,
        region: str,
        interests: Optional[List[str]] = None,
        days: Optional[int] = None,
        budget: Optional[str] = None,
        travelers: Optional[int] = None,
        travel_style: Optional[str] = None,
        limit: int = 6,
    ) -> MCPToolResponse:
        return self.call_tool(
            tool_name="recommend_cities_in_region",
            arguments={
                "region": region,
                "interests": interests or [],
                "days": days,
                "budget": budget,
                "travelers": travelers,
                "travel_style": travel_style,
                "limit": limit,
            },
        )

    def rank_places(
        self,
        city: str,
        places: List[Dict[str, Any]],
        interests: Optional[List[str]] = None,
        days: Optional[int] = None,
    ) -> MCPToolResponse:
        return self.call_tool(
            tool_name="rank_places",
            arguments={
                "city": city,
                "places": places or [],
                "interests": interests or [],
                "days": days,
            },
        )
