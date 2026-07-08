from typing import Any, Dict, List, Optional

from config.constants import AGENT_TRANSPORT
from schemas.agent_schema import AgentInput, AgentOutput, AgentMetadata
from agents_mcp.base_agent import BaseAgent
from mcp_clients.transport_mcp_client import TransportMCPClient


class TransportAgent(BaseAgent):
    """
    Builds the trip's structured travel sequence.

    Responsibility:
    - Use TransportMCPClient / transport MCP tools for route data.
    - Order attractions inside each city when coordinates are available.
    - Order cities when coordinates are available.
    - Fetch real transfer legs between source/cities.
    - Produce a rich display_sequence that the final composer can render.

    FinalResponseComposer must not build routing logic itself. It should only
    describe the sequence prepared here.
    """

    def __init__(self):
        metadata = AgentMetadata(
            name=AGENT_TRANSPORT,
            description="Builds inter-city transfer sequence and intra-city POI movement flow.",
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

    # ------------------------------------------------------------------ #
    # Multi-city / hierarchical destination flow
    # ------------------------------------------------------------------ #

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
                if isinstance(place, dict)
                and place.get("latitude") is not None
                and place.get("longitude") is not None
                and place.get("name")
            ]

            ordered_attractions = usable_places
            intra_city_distance_km = 0.0
            intra_city_route_success = False

            if len(usable_places) > 1:
                route_response = self.client.optimize_route(points=usable_places, start_index=0)

                if route_response.success and route_response.data.get("success"):
                    ordered_attractions = route_response.data.get("ordered_points", usable_places)
                    intra_city_distance_km = route_response.data.get("total_distance_km", 0.0)
                    intra_city_route_success = True

            city_blocks.append(
                {
                    "city": city,
                    "ordered_attractions": self._compact_pois(ordered_attractions),
                    "intra_city_distance_km": intra_city_distance_km,
                    "intra_city_route_success": intra_city_route_success,
                    "poi_count": len(ordered_attractions),
                }
            )

            centroid = self._centroid(usable_places)

            if centroid is not None:
                city_points.append(
                    {
                        "name": city,
                        "latitude": centroid[0],
                        "longitude": centroid[1],
                    }
                )

        ordered_city_names = selected_cities

        if len(city_points) == len(selected_cities) and len(city_points) > 1:
            city_route_response = self.client.optimize_route(points=city_points, start_index=0)

            if city_route_response.success and city_route_response.data.get("success"):
                ordered_city_names = [
                    point.get("name")
                    for point in city_route_response.data.get("ordered_points", city_points)
                    if point.get("name")
                ]

        city_blocks_by_name = {block["city"]: block for block in city_blocks}
        ordered_city_blocks = [
            city_blocks_by_name[name]
            for name in ordered_city_names
            if name in city_blocks_by_name
        ]

        inter_city_legs = self._fetch_inter_city_legs(agent_input, ordered_city_names)
        travel_sequence = self._assemble_sequence(ordered_city_blocks, inter_city_legs)
        display_sequence = self._build_display_sequence(ordered_city_blocks, inter_city_legs)

        return self.success_response(
            data={
                "mode": "multi_city_sequence",
                "source": agent_input.source,
                "ordered_cities": ordered_city_names,
                "city_blocks": ordered_city_blocks,
                "inter_city_legs": inter_city_legs,
                "travel_sequence": travel_sequence,
                "display_sequence": display_sequence,
                "sequence_note": (
                    "display_sequence is the prepared user-facing travel flow. "
                    "Final composer should render this sequence, not rebuild routing logic."
                ),
            },
            message="Multi-city travel sequence built successfully.",
        )

    def _fetch_inter_city_legs(
        self,
        agent_input: AgentInput,
        ordered_city_names: List[str],
    ) -> List[Dict[str, Any]]:
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

            transport_data = response.data if response.success else None
            compact_transport_data = self._compact_transport_data(transport_data)

            legs.append(
                {
                    "from": from_city,
                    "to": to_city,
                    "success": response.success,
                    "transport_data": compact_transport_data,
                    "error": response.error if not response.success else None,
                }
            )

        return legs

    def _assemble_sequence(
        self,
        ordered_city_blocks: List[Dict[str, Any]],
        inter_city_legs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        sequence: List[Dict[str, Any]] = []
        used_leg_indexes = set()

        for block in ordered_city_blocks:
            city = block["city"]

            matching_leg_index = None
            matching_leg = None

            for index, leg in enumerate(inter_city_legs):
                if index in used_leg_indexes:
                    continue

                if leg.get("to") == city:
                    matching_leg_index = index
                    matching_leg = leg
                    break

            if matching_leg is not None:
                sequence.append({"type": "transfer", **matching_leg})
                used_leg_indexes.add(matching_leg_index)

            sequence.append(
                {
                    "type": "city_visit",
                    "city": city,
                    "ordered_attractions": block.get("ordered_attractions", []),
                    "intra_city_distance_km": block.get("intra_city_distance_km", 0.0),
                    "intra_city_route_success": block.get("intra_city_route_success", False),
                }
            )

        return sequence

    def _build_display_sequence(
        self,
        ordered_city_blocks: List[Dict[str, Any]],
        inter_city_legs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        This is the final structured sequence that the composer should render.

        Example:
        [
          {"type": "transfer", "from": "Delhi", "to": "Puri", ...},
          {"type": "city_flow", "city": "Puri", "pois": [...]},
          {"type": "transfer", "from": "Puri", "to": "Konark", ...},
          {"type": "city_flow", "city": "Konark", "pois": [...]}
        ]
        """
        display_sequence: List[Dict[str, Any]] = []
        used_leg_indexes = set()

        for block in ordered_city_blocks:
            city = block.get("city")

            matching_leg_index = None
            matching_leg = None

            for index, leg in enumerate(inter_city_legs):
                if index in used_leg_indexes:
                    continue

                if leg.get("to") == city:
                    matching_leg_index = index
                    matching_leg = leg
                    break

            if matching_leg is not None:
                transport_data = matching_leg.get("transport_data") or {}

                display_sequence.append(
                    {
                        "type": "transfer",
                        "from": matching_leg.get("from"),
                        "to": matching_leg.get("to"),
                        "success": matching_leg.get("success"),
                        "mode": transport_data.get("mode") or "driving-car",
                        "distance_km": transport_data.get("distance_km"),
                        "duration_hours": transport_data.get("duration_hours"),
                        "duration_minutes": transport_data.get("duration_minutes"),
                        "route_source": transport_data.get("route_source"),
                        "note": self._transfer_note(
                            from_city=matching_leg.get("from"),
                            to_city=matching_leg.get("to"),
                            transport_data=transport_data,
                            success=matching_leg.get("success"),
                            error=matching_leg.get("error"),
                        ),
                    }
                )

                used_leg_indexes.add(matching_leg_index)

            pois = block.get("ordered_attractions") or []

            display_sequence.append(
                {
                    "type": "city_flow",
                    "city": city,
                    "pois": pois,
                    "poi_names": [poi.get("name") for poi in pois if poi.get("name")],
                    "intra_city_distance_km": block.get("intra_city_distance_km", 0.0),
                    "intra_city_route_success": block.get("intra_city_route_success", False),
                    "note": self._city_flow_note(block),
                }
            )

        return display_sequence

    def _transfer_note(
        self,
        from_city: Optional[str],
        to_city: Optional[str],
        transport_data: Dict[str, Any],
        success: bool,
        error: Optional[str],
    ) -> str:
        if not success:
            return (
                f"Could not fetch a reliable road route from {from_city} to {to_city}. "
                f"Reason: {error or 'unknown error'}."
            )

        distance_km = transport_data.get("distance_km")
        duration_hours = transport_data.get("duration_hours")

        if isinstance(distance_km, (int, float)) and distance_km >= 700:
            return "Long-distance transfer. Consider flight or train instead of a full road journey."

        if isinstance(duration_hours, (int, float)) and duration_hours >= 8:
            return "Long road transfer. Keep this as a dedicated travel block."

        if isinstance(duration_hours, (int, float)) and duration_hours >= 4:
            return "Moderate-to-long road transfer. Start early and keep buffer time."

        return "Local or short inter-city transfer."

    def _city_flow_note(self, block: Dict[str, Any]) -> str:
        poi_count = block.get("poi_count", 0)
        route_success = block.get("intra_city_route_success", False)

        if poi_count == 0:
            return "No reliable POI coordinates were available for local ordering."

        if route_success:
            return "POIs are ordered using route optimization where coordinate data was available."

        return "POIs are listed in available ranked order; route optimization was not fully available."

    # ------------------------------------------------------------------ #
    # Single-city / legacy flow
    # ------------------------------------------------------------------ #

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

        compact_transport_data = self._compact_transport_data(response.data)

        display_sequence = [
            {
                "type": "transfer",
                "from": agent_input.source,
                "to": agent_input.destination,
                "success": True,
                "mode": compact_transport_data.get("mode") or "driving-car",
                "distance_km": compact_transport_data.get("distance_km"),
                "duration_hours": compact_transport_data.get("duration_hours"),
                "duration_minutes": compact_transport_data.get("duration_minutes"),
                "route_source": compact_transport_data.get("route_source"),
                "note": self._transfer_note(
                    from_city=agent_input.source,
                    to_city=agent_input.destination,
                    transport_data=compact_transport_data,
                    success=True,
                    error=None,
                ),
            }
        ]

        return self.success_response(
            data={
                "mode": "single_leg",
                "source": agent_input.source,
                "destination": agent_input.destination,
                "raw_transport_data": compact_transport_data,
                "display_sequence": display_sequence,
                "raw_mcp_response": response.raw_response,
            },
            message="Transport data fetched successfully.",
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _compact_transport_data(self, transport_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not isinstance(transport_data, dict):
            return {}

        distance_km = (
            transport_data.get("distance_km")
            or transport_data.get("distance")
            or transport_data.get("estimated_distance_km")
        )

        duration_hours = (
            transport_data.get("duration_hours")
            or transport_data.get("duration")
            or transport_data.get("estimated_duration_hours")
        )

        duration_minutes = transport_data.get("duration_minutes")

        if duration_minutes is None and isinstance(duration_hours, (int, float)):
            duration_minutes = round(duration_hours * 60)

        return {
            "source": transport_data.get("source"),
            "destination": transport_data.get("destination"),
            "mode": transport_data.get("mode") or "driving-car",
            "distance_km": self._round_number(distance_km),
            "duration_hours": self._round_number(duration_hours),
            "duration_minutes": self._round_number(duration_minutes),
            "route_source": (
                transport_data.get("route_source")
                or transport_data.get("source_api")
                or transport_data.get("provider")
                or "transport_service"
            ),
            "note": transport_data.get("note"),
            "raw_summary": transport_data.get("summary"),
        }

    def _compact_pois(self, pois: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        compact = []

        for poi in pois:
            if not isinstance(poi, dict):
                continue

            name = poi.get("name")

            if not name:
                continue

            compact.append(
                {
                    "name": name,
                    "categories": poi.get("categories") or poi.get("category") or [],
                    "formatted_address": poi.get("formatted_address"),
                    "latitude": poi.get("latitude"),
                    "longitude": poi.get("longitude"),
                    "distance_meters": poi.get("distance_meters") or poi.get("distance"),
                    "source": poi.get("source"),
                }
            )

        return compact

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

        return avg_lat, avg_lon

    @staticmethod
    def _round_number(value: Any):
        if isinstance(value, float):
            return round(value, 2)

        return value