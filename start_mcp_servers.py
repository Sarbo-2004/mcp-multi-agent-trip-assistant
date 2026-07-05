import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

SERVERS = [
    {
        "name": "Places MCP Server",
        "module": "mcp_servers.places_mcp_server",
        "port": 8001,
    },
    {
        "name": "Climate MCP Server",
        "module": "mcp_servers.climate_mcp_server",
        "port": 8002,
    },
    {
        "name": "Transport MCP Server",
        "module": "mcp_servers.transport_mcp_server",
        "port": 8003,
    },
    {
        "name": "Hotel MCP Server",
        "module": "mcp_servers.hotel_mcp_server",
        "port": 8004,
    },
]


def start_servers():
    processes = []

    print("Starting MCP servers...\n")

    for server in SERVERS:
        print(f"Starting {server['name']} on port {server['port']}...")

        process = subprocess.Popen(
            [sys.executable, "-m", server["module"]],
            cwd=PROJECT_ROOT,
        )

        processes.append(
            {
                "name": server["name"],
                "port": server["port"],
                "process": process,
            }
        )

        time.sleep(1)

    print("\nAll MCP servers started.")
    print("Press CTRL + C to stop all servers.\n")

    try:
        while True:
            time.sleep(2)

            for item in processes:
                process = item["process"]

                if process.poll() is not None:
                    print(f"{item['name']} stopped unexpectedly on port {item['port']}.")

    except KeyboardInterrupt:
        print("\nStopping MCP servers...")

        for item in processes:
            process = item["process"]

            if process.poll() is None:
                print(f"Stopping {item['name']}...")
                process.terminate()

        time.sleep(2)

        for item in processes:
            process = item["process"]

            if process.poll() is None:
                process.kill()

        print("All MCP servers stopped.")


if __name__ == "__main__":
    start_servers()