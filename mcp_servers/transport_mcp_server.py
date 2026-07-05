import json
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from services.transport_service import TransportService


mcp = FastMCP(
    "transport_mcp_server",
    host="127.0.0.1",
    port=8003,
    json_response=True,
)

transport_service = TransportService()


@mcp.tool()
def get_transport_options(
    source: str,
    destination: str,
    mode: str = "driving-car",
) -> str:
    result: Dict[str, Any] = transport_service.get_transport_options(
        source=source,
        destination=destination,
        mode=mode,
    )

    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def optimize_route(
    points: List[Dict[str, Any]],
    start_index: int = 0,
) -> str:
    result: Dict[str, Any] = transport_service.optimize_route(
        points=points or [],
        start_index=start_index,
    )

    return json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")