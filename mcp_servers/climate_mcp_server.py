import json
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from services.weather_service import WeatherService


mcp = FastMCP(
    "climate_mcp_server",
    host="127.0.0.1",
    port=8002,
    json_response=True,
)

weather_service = WeatherService()


@mcp.tool()
def get_climate(
    destination: str,
    month: Optional[str] = None,
    travel_dates: Optional[Dict[str, str]] = None,
) -> str:
    result: Dict[str, Any] = weather_service.get_climate(
        destination=destination,
        month=month,
        travel_dates=travel_dates,
    )

    return json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")