import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()
from typing import Optional
from pydantic_settings import BaseSettings

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
    ssl_verify: bool = str_to_bool(
        os.getenv("SSL_VERIFY", os.getenv("VERIFY_SSL", "true")),
        default=True,
    )
    geoapify_ssl_verify: bool = str_to_bool(
        os.getenv(
            "GEOAPIFY_VERIFY_SSL",
            os.getenv("GEOAPIFY_SSL_VERIFY", os.getenv("SSL_VERIFY", os.getenv("VERIFY_SSL", "true"))),
        ),
        default=True,
    )
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "30"))

class RedisSettings(BaseSettings):
    redis_enabled: bool = False
    redis_url: Optional[str] = None

    redis_ttl_seconds: int = 86400
    redis_namespace: str = "trip_memory"

    redis_socket_timeout: int = 10
    redis_socket_connect_timeout: int = 10

    class Config:
        env_file = ".env"
        extra = "ignore"


redis_settings = RedisSettings()

app_settings = AppSettings()
mcp_settings = MCPSettings()
api_settings = APISettings()
network_settings = NetworkSettings()