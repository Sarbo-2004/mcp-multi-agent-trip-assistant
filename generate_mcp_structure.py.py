from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

folders = [
    "config",
    "schemas",
    "services",
    "mcp_servers_http",
    "mcp_clients",
    "agents_mcp",
    "orchestrator",
    "utils",
]

files = {
    "app_mcp.py": "",
    "requirements.txt": "",
    ".env": "",
    "README.md": "",

    "config/__init__.py": "",
    "config/settings.py": "",
    "config/constants.py": "",

    "schemas/__init__.py": "",
    "schemas/trip_schema.py": "",
    "schemas/agent_schema.py": "",
    "schemas/mcp_schema.py": "",

    "services/__init__.py": "",
    "services/places_service.py": "",
    "services/weather_service.py": "",
    "services/transport_service.py": "",
    "services/hotel_service.py": "",

    "mcp_servers_http/__init__.py": "",
    "mcp_servers_http/places_http_server.py": "",
    "mcp_servers_http/climate_http_server.py": "",
    "mcp_servers_http/transport_http_server.py": "",
    "mcp_servers_http/hotel_http_server.py": "",

    "mcp_clients/__init__.py": "",
    "mcp_clients/base_http_mcp_client.py": "",
    "mcp_clients/places_mcp_client.py": "",
    "mcp_clients/climate_mcp_client.py": "",
    "mcp_clients/transport_mcp_client.py": "",
    "mcp_clients/hotel_mcp_client.py": "",

    "agents_mcp/__init__.py": "",
    "agents_mcp/base_agent.py": "",
    "agents_mcp/destination_agent.py": "",
    "agents_mcp/climate_agent.py": "",
    "agents_mcp/transport_agent.py": "",
    "agents_mcp/hotel_agent.py": "",
    "agents_mcp/itinerary_agent.py": "",
    "agents_mcp/budget_agent.py": "",

    "orchestrator/__init__.py": "",
    "orchestrator/intent_analyzer.py": "",
    "orchestrator/workflow_planner.py": "",
    "orchestrator/dynamic_executor.py": "",
    "orchestrator/trip_orchestrator.py": "",

    "utils/__init__.py": "",
    "utils/logger.py": "",
    "utils/response_formatter.py": "",
    "utils/validators.py": "",
}


def create_project_structure():
    print("Creating MCP-based multi-agent trip system structure...\n")

    for folder in folders:
        folder_path = PROJECT_ROOT / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        print(f"Created folder: {folder_path}")

    print()

    for file_path, content in files.items():
        full_path = PROJECT_ROOT / file_path

        if full_path.exists():
            print(f"Skipped existing file: {full_path}")
            continue

        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        print(f"Created file: {full_path}")

    print("\nFolder structure generated successfully.")


if __name__ == "__main__":
    create_project_structure()