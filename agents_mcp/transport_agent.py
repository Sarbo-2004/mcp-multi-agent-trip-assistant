from typing import Any, Dict, List, Optional

from config.constants import AGENT_TRANSPORT
from schemas.agent_schema import AgentInput, AgentOutput, AgentMetadata
from agents_mcp.base_agent import BaseAgent
from mcp_clients.transport_mcp_client import TransportMCPClient


class TransportAgent(BaseAgent):
    """Builds the trip's travel sequence.

    When per-city attraction data is available (hierarchical destination
    planning), this agent never mixes attractions across cities. It:
      1. Optimizes the visiting order of attractions *inside* each city.
      2. Optimizes the order in which cities are visited.
      3. Stitches both into one final travel sequence, with real
         source→destination legs fetched between consecutive cities.

    Falls back to a single source→destination lookup when no per-city
    attraction data is present in the input context (single-city / legacy
    queries), preserving prior behavior.
    """

    def __init__(self):
        metadata = AgentMetadata(
            name=AGENT_TRANSPORT,
            description="Builds an intra-city and inter-city ordered travel sequence.",
            depends_on=[],
            output_key="transport_result",
        )
        super().__init__(metadata)
        self.client = TransportMCPClient()

    def run(self, agent_input: AgentInput) -> AgentOutput:
        city_attractions = agent_input.context.get("city_attractions") or {}

        if city_attractions:
            return self._build_multi_city_sequence(agent_input, city_attractions)

        return self._fetch_single_leg(agent_input)

    def _build_multi_city_sequence(
        self,
        agent_input: AgentInput,
        city_attractions: Dict[str, Any],
    ) -> AgentOutput:
        selected_cities = agent_input.context.get("selected_cities") or list(city_attractions.keys())
        selected_cities = [city for city in selected_cities if city in city_attractions]

        if not selected_cities:
            return self.error_response(
                error="No valid selected cities found in city_attractions context.",
                data={"mode": "multi_city_sequence"},
            )

        city_blocks: List[Dict[str, Any]] = []
        city_points: List[Dict[str, Any]] = []

        for city in selected_cities:
            places = city_attractions.get(city, {}).get("ranked_places") or []
            usable_places = [
                place for place in places
                if place.get("latitude") is not None and place.get("longitude") is not None
            ]

            ordered_attractions = usable_places
            intra_city_distance_km = 0.0

            if usable_places:
                route_response = self.client.optimize_route(points=usable_places, start_index=0)

                if route_response.success and route_response.data.get("success"):
                    ordered_attractions = route_response.data.get("ordered_points", usable_places)
                    intra_city_distance_km = route_response.data.get("total_distance_km", 0.0)

            city_blocks.append({
                "city": city,
                "ordered_attractions": ordered_attractions,
                "intra_city_distance_km": intra_city_distance_km,
            })

            centroid = self._centroid(usable_places)

            if centroid is not None:
                city_points.append({
                    "name": city,
                    "latitude": centroid[0],
                    "longitude": centroid[1],
                })

        ordered_city_names = selected_cities

        if len(city_points) == len(selected_cities) and len(city_points) > 1:
            city_route_response = self.client.optimize_route(points=city_points, start_index=0)

            if city_route_response.success and city_route_response.data.get("success"):
                ordered_city_names = [
                    point.get("name") for point in city_route_response.data.get("ordered_points", city_points)
                ]

        city_blocks_by_name = {block["city"]: block for block in city_blocks}
        ordered_city_blocks = [city_blocks_by_name[name] for name in ordered_city_names if name in city_blocks_by_name]

        inter_city_legs = self._fetch_inter_city_legs(agent_input, ordered_city_names)

        travel_sequence = self._assemble_sequence(ordered_city_blocks, inter_city_legs)

        return self.success_response(
            data={
                "mode": "multi_city_sequence",
                "ordered_cities": ordered_city_names,
                "city_blocks": ordered_city_blocks,
                "inter_city_legs": inter_city_legs,
                "travel_sequence": travel_sequence,
            },
            message="Multi-city travel sequence built successfully.",
        )

    def _fetch_inter_city_legs(self, agent_input: AgentInput, ordered_city_names: List[str]) -> List[Dict[str, Any]]:
        legs: List[Dict[str, Any]] = []

        waypoints = list(ordered_city_names)

        if agent_input.source:
            waypoints = [agent_input.source] + waypoints

        for from_city, to_city in zip(waypoints, waypoints[1:]):
            response = self.client.get_transport_options(
                source=from_city,
                destination=to_city,
                mode="driving-car",
            )

            legs.append({
                "from": from_city,
                "to": to_city,
                "success": response.success,
                "transport_data": response.data if response.success else None,
                "error": response.error if not response.success else None,
            })

        return legs

    def _assemble_sequence(
        self,
        ordered_city_blocks: List[Dict[str, Any]],
        inter_city_legs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        legs_by_pair = {(leg["from"], leg["to"]): leg for leg in inter_city_legs}
        sequence: List[Dict[str, Any]] = []

        previous_city: Optional[str] = None

        for block in ordered_city_blocks:
            city = block["city"]

            leg = next((legs_by_pair[pair] for pair in legs_by_pair if pair[1] == city and (previous_city is None or pair[0] == previous_city)), None)

            if leg is not None:
                sequence.append({"type": "travel", **leg})

            sequence.append({
                "type": "city_visit",
                "city": city,
                "ordered_attractions": block["ordered_attractions"],
                "intra_city_distance_km": block["intra_city_distance_km"],
            })

            previous_city = city

        return sequence

    @staticmethod
    def _centroid(places: List[Dict[str, Any]]):
        coords = [
            (place["latitude"], place["longitude"])
            for place in places
            if place.get("latitude") is not None and place.get("longitude") is not None
        ]

        if not coords:
            return None

        avg_lat = sum(lat for lat, _ in coords) / len(coords)
        avg_lon = sum(lon for _, lon in coords) / len(coords)

        return (avg_lat, avg_lon)

    def _fetch_single_leg(self, agent_input: AgentInput) -> AgentOutput:
        if not agent_input.source:
            return self.error_response("Source is required for transport agent.")

        if not agent_input.destination:
            return self.error_response("Destination is required for transport agent.")

        response = self.client.get_transport_options(
            source=agent_input.source,
            destination=agent_input.destination,
            mode="driving-car",
        )

        if not response.success:
            return self.error_response(
                error=response.error or "Failed to fetch transport data.",
                data={
                    "mode": "single_leg",
                    "raw_mcp_response": response.raw_response,
                },
            )

        return self.success_response(
            data={
                "mode": "single_leg",
                "source": agent_input.source,
                "destination": agent_input.destination,
                "raw_transport_data": response.data,
                "raw_mcp_response": response.raw_response,
            },
            message="Raw transport data fetched successfully.",
        )
