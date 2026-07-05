import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def str_to_bool(value: str, default: bool = True) -> bool:
    if value is None:
        return default

    return value.strip().lower() in ["true", "1", "yes", "y"]


def normalize_mcp_url(url: str, use_mcp_path: bool = True) -> str:
    url = url.rstrip("/")

    if use_mcp_path and not url.endswith("/mcp"):
        url = f"{url}/mcp"

    return url


@dataclass
class AppSettings:
    app_name: str = "Dynamic MCP Multi-Agent Trip Planner"
    app_version: str = "1.0.0"
    debug: bool = str_to_bool(os.getenv("DEBUG", "false"), default=False)


@dataclass
class MCPSettings:
    places_mcp_url: str = normalize_mcp_url(
        os.getenv("PLACES_MCP_URL", "http://127.0.0.1:8001/mcp")
    )

    climate_mcp_url: str = normalize_mcp_url(
        os.getenv("CLIMATE_MCP_URL", "http://127.0.0.1:8002/mcp")
    )

    transport_mcp_url: str = normalize_mcp_url(
        os.getenv("TRANSPORT_MCP_URL", "http://127.0.0.1:8003/mcp")
    )

    hotel_mcp_url: str = normalize_mcp_url(
        os.getenv("HOTEL_MCP_URL", "http://127.0.0.1:8004/mcp")
    )

    timeout: int = int(os.getenv("MCP_TIMEOUT", "30"))


@dataclass
class APISettings:
    geoapify_api_key: str = os.getenv("GEOAPIFY_API_KEY", "")
    openrouteservice_api_key: str = os.getenv("OPENROUTESERVICE_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")


@dataclass
class NetworkSettings:
    ssl_verify: bool = str_to_bool(os.getenv("SSL_VERIFY", "true"), default=True)
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "30"))


app_settings = AppSettings()
mcp_settings = MCPSettings()
api_settings = APISettings()
network_settings = NetworkSettings()