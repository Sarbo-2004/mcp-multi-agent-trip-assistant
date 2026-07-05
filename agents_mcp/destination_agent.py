from config.constants import AGENT_DESTINATION, SCOPE_CITY, BROAD_SCOPES, SCOPE_UNKNOWN
from schemas.agent_schema import AgentInput, AgentOutput, AgentMetadata
from agents_mcp.base_agent import BaseAgent
from mcp_clients.places_mcp_client import PlacesMCPClient


class DestinationAgent(BaseAgent):
    """Owns all destination/places business logic: recommending a destination
    when none is given, classifying a given destination's scope (city vs
    state/region/country), recommending cities inside a broad scope, and
    fetching + ranking attractions for one resolved city at a time.

    Attractions are always fetched per city, never for an entire region — the
    ``attractions`` graph node calls ``run`` once per selected city with
    ``agent_input.context["destination_mode"] = "fetch_attractions"``.
    """

    def __init__(self):
        metadata = AgentMetadata(
            name=AGENT_DESTINATION,
            description=(
                "Recommends destinations, classifies destination scope, recommends "
                "cities within a broad region, and fetches/ranks per-city attractions."
            ),
            depends_on=[],
            output_key="destination_result",
        )
        super().__init__(metadata)
        self.client = PlacesMCPClient()

    def run(self, agent_input: AgentInput) -> AgentOutput:
        destination_mode = agent_input.context.get("destination_mode")

        if destination_mode == "fetch_attractions":
            return self._fetch_and_rank_attractions_for_city(agent_input)

        if not agent_input.destination:
            return self._recommend_destinations(agent_input)

        return self._resolve_scope(agent_input)

    def _resolve_scope(self, agent_input: AgentInput) -> AgentOutput:
        classify_response = self.client.classify_destination(agent_input.destination)

        if not classify_response.success:
            return self.error_response(
                error=classify_response.error or "Failed to classify destination.",
                data={
                    "mode": "scope_classification",
                    "destination": agent_input.destination,
                    "raw_mcp_response": classify_response.raw_response,
                },
            )

        scope = classify_response.data.get("scope", SCOPE_UNKNOWN)
        canonical_name = classify_response.data.get("canonical_name") or agent_input.destination

        if scope == SCOPE_UNKNOWN:
            return self.error_response(
                error=(
                    f"Could not determine whether '{agent_input.destination}' is a city "
                    "or a broader state/region/country."
                ),
                data={
                    "mode": "scope_classification",
                    "destination": agent_input.destination,
                    "scope": scope,
                },
            )

        if scope == SCOPE_CITY:
            return self.success_response(
                data={
                    "mode": "scope_resolved",
                    "scope": scope,
                    "destination": agent_input.destination,
                    "resolved_cities": [canonical_name],
                },
                message=f"'{canonical_name}' resolved as a single city.",
            )

        if scope in BROAD_SCOPES:
            return self._recommend_cities_in_region(agent_input, region=canonical_name, scope=scope)

        return self.error_response(
            error=f"Unsupported destination scope '{scope}'.",
            data={"mode": "scope_classification", "destination": agent_input.destination, "scope": scope},
        )

    def _recommend_cities_in_region(self, agent_input: AgentInput, region: str, scope: str) -> AgentOutput:
        response = self.client.recommend_cities_in_region(
            region=region,
            interests=agent_input.interests,
            days=agent_input.days,
            budget=agent_input.budget,
            travelers=agent_input.travelers,
            travel_style=agent_input.context.get("travel_style"),
            limit=6,
        )

        if not response.success:
            return self.error_response(
                error=response.error or f"Failed to recommend cities within '{region}'.",
                data={
                    "mode": "city_recommendation",
                    "scope": scope,
                    "region": region,
                    "raw_mcp_response": response.raw_response,
                },
            )

        return self.success_response(
            data={
                "mode": "city_recommendation",
                "scope": scope,
                "region": region,
                "city_recommendations": response.data.get("recommendations", []),
            },
            message=f"Candidate cities recommended for '{region}'.",
        )

    def _fetch_and_rank_attractions_for_city(self, agent_input: AgentInput) -> AgentOutput:
        city = agent_input.context.get("target_city") or agent_input.destination

        if not city:
            return self.error_response(
                error="A target city is required to fetch attractions.",
                data={"mode": "city_attractions"},
            )

        places_response = self.client.get_popular_places(
            destination=city,
            interests=agent_input.interests,
            limit=10,
        )

        if not places_response.success:
            return self.error_response(
                error=places_response.error or f"Failed to fetch places for '{city}'.",
                data={
                    "mode": "city_attractions",
                    "city": city,
                    "raw_mcp_response": places_response.raw_response,
                },
            )

        places = places_response.data.get("places", [])

        rank_response = self.client.rank_places(
            city=city,
            places=places,
            interests=agent_input.interests,
            days=agent_input.days,
        )

        ranked_places = places

        if rank_response.success:
            ranked_places = rank_response.data.get("ranked_places", places)

        return self.success_response(
            data={
                "mode": "city_attractions",
                "city": city,
                "interests": agent_input.interests,
                "places": places,
                "ranked_places": ranked_places,
            },
            message=f"Attractions fetched and ranked for '{city}'.",
        )

    def _recommend_destinations(self, agent_input: AgentInput) -> AgentOutput:
        response = self.client.recommend_destinations(
            source=agent_input.source,
            interests=agent_input.interests,
            month=agent_input.month,
            budget=agent_input.budget,
            days=agent_input.days,
            travelers=agent_input.travelers,
            limit=8,
        )

        if not response.success:
            return self.error_response(
                error=response.error or "Failed to recommend destinations.",
                data={
                    "mode": "destination_recommendation",
                    "source": agent_input.source,
                    "interests": agent_input.interests,
                    "month": agent_input.month,
                    "budget": agent_input.budget,
                    "days": agent_input.days,
                    "travelers": agent_input.travelers,
                    "raw_mcp_response": response.raw_response,
                },
            )

        return self.success_response(
            data={
                "mode": "destination_recommendation",
                "source": agent_input.source,
                "interests": agent_input.interests,
                "month": agent_input.month,
                "budget": agent_input.budget,
                "days": agent_input.days,
                "travelers": agent_input.travelers,
                "recommended_destinations": response.data,
                "raw_mcp_response": response.raw_response,
            },
            message="Destination recommendations generated successfully.",
        )
