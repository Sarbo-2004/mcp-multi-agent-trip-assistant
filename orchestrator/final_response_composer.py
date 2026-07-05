import html
import json
from typing import Any, Dict, List

import google.generativeai as genai

from config.settings import api_settings
from schemas.trip_schema import TripState


class FinalResponseComposer:
    """Turns a finished ``TripState`` into the user-facing plan.

    By the time this runs, destination hierarchy has already been resolved
    structurally by the graph (region -> city recommendations -> user
    selection happens before ``compose`` is ever reached), so this composer
    always writes a concrete, city-grouped itinerary rather than branching on
    destination scope.
    """

    def __init__(self):
        self.model = None

        if api_settings.gemini_api_key:
            genai.configure(api_key=api_settings.gemini_api_key)
            self.model = genai.GenerativeModel(api_settings.gemini_model)

    def compose(self, state: TripState) -> Dict[str, Any]:
        if not self.model:
            return {
                "success": False,
                "error": "Gemini API key is missing. Final response composition skipped.",
                "response": None,
            }

        payload = self._build_payload(state)
        compact_payload = self._compact_payload(payload)
        prompt = self._build_prompt(compact_payload)

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.25,
                    "top_p": 0.8,
                    "top_k": 40,
                },
            )

            text = getattr(response, "text", "").strip()

            if not text:
                return {
                    "success": False,
                    "error": "Gemini returned empty final response.",
                    "response": None,
                    "input_payload": compact_payload,
                }

            return {
                "success": True,
                "response": html.unescape(text),
                "input_payload": compact_payload,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Final response composition failed: {type(e).__name__}: {str(e)}",
                "response": None,
                "input_payload": compact_payload,
            }

    def _build_payload(self, state: TripState) -> Dict[str, Any]:
        return {
            "request": state.get("request", {}),
            "selected_cities": state.get("selected_cities", []),
            "city_attractions": state.get("city_attractions", {}),
            "agent_results": state.get("agent_results", {}),
            "travel_sequence": state.get("travel_sequence"),
            "feasible": state.get("feasible"),
            "replan_directives": state.get("replan_directives", []),
            "errors": state.get("errors", []),
        }

    def _compact_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        request = payload.get("request", {})
        agent_results = payload.get("agent_results", {})
        city_attractions = payload.get("city_attractions", {})

        compact_cities = {}

        for city, data in city_attractions.items():
            places = (data or {}).get("ranked_places") or (data or {}).get("places") or []
            filtered = self._filter_high_quality_places(places)

            compact_cities[city] = {
                "places_available": len(filtered) > 0,
                "poi_quality": "usable" if len(filtered) >= 3 else "weak",
                "places": filtered[:8],
            }

        climate_by_city = self._safe_get(agent_results, ["climate_agent", "data", "by_city"]) or {}
        hotel_by_city = self._safe_get(agent_results, ["hotel_agent", "data", "by_city"]) or {}
        itinerary_result = self._safe_get(agent_results, ["itinerary_agent", "data"]) or {}
        budget_result = self._safe_get(agent_results, ["budget_agent", "data"]) or {}

        compact_climate = {
            city: self._safe_get(result, ["data", "raw_climate_data"])
            for city, result in climate_by_city.items()
        }

        compact_hotel = {
            city: self._safe_get(result, ["data", "raw_hotel_data"])
            for city, result in hotel_by_city.items()
        }

        return {
            "request": request,
            "selected_cities": payload.get("selected_cities", []),
            "city_attractions": compact_cities,
            "climate_by_city": compact_climate,
            "hotel_by_city": compact_hotel,
            "travel_sequence": payload.get("travel_sequence"),
            "itinerary_skeleton": itinerary_result,
            "budget_result": budget_result,
            "feasible": payload.get("feasible"),
            "replan_directives": payload.get("replan_directives", []),
            "errors": payload.get("errors", []),
            "composer_instruction": (
                "Use named POIs for a city only if that city's poi_quality is usable. "
                "If poi_quality is weak for a city, describe that city's day(s) at a high level "
                "using destination, interests, climate, transport, hotel, and budget context instead "
                "of inventing place names."
            ),
        }

    def _filter_high_quality_places(self, places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not places:
            return []

        preferred_category_terms = [
            "tourism",
            "attraction",
            "natural",
            "beach",
            "leisure",
            "heritage",
            "museum",
            "park",
            "viewpoint",
            "zoo",
            "garden",
            "waterfall",
            "fort",
            "palace",
            "temple",
            "church",
            "monument",
        ]

        weak_or_non_itinerary_terms = [
            "catering",
            "restaurant",
            "cafe",
            "bar",
            "pub",
            "accommodation",
            "hotel",
            "hostel",
            "guest_house",
            "apartment",
            "commercial",
            "bank",
            "office",
        ]

        filtered = []

        for item in places:
            if not isinstance(item, dict):
                continue

            name = self._clean_text(item.get("name"))

            if not name:
                continue

            categories = item.get("category") or item.get("categories") or []

            if isinstance(categories, str):
                categories = [categories]

            category_text = " ".join(str(category).lower() for category in categories)

            has_preferred = any(term in category_text for term in preferred_category_terms)
            has_weak = any(term in category_text for term in weak_or_non_itinerary_terms)

            if has_weak and not has_preferred:
                continue

            if not has_preferred:
                continue

            filtered.append(
                {
                    "name": name,
                    "category": categories,
                    "formatted_address": self._clean_text(item.get("formatted_address")),
                    "distance_meters": item.get("distance_meters"),
                }
            )

        return filtered

    def _safe_get(self, data: Dict[str, Any], path: list, default=None):
        current = data

        for key in path:
            if not isinstance(current, dict):
                return default

            current = current.get(key)

            if current is None:
                return default

        return current

    def _clean_text(self, value):
        if value is None:
            return None

        if not isinstance(value, str):
            return value

        return html.unescape(value).strip()

    def _build_prompt(self, payload: Dict[str, Any]) -> str:
        return f"""
You are a professional AI trip planning assistant.

Your job is to compose the final user-facing travel response using structured outputs from multiple agents, covering one or more cities.

Architecture rule:
- Agents provide raw facts.
- You generate final reasoning, advice, and itinerary.
- Do not expose internal JSON or agent names.

General rules:
1. Do not invent exact transport numbers. Use travel_sequence data only if present.
2. Do not invent exact hotel names if hotel POIs are missing for a city.
3. Do not blindly use restaurant, cafe, hotel, bank, street, statue, office, or random local POI names as main attractions.
4. For any city where poi_quality is "weak", do not mention that city's POI names.
5. Where POIs are weak, create a high-level plan for that city's days based on:
   - the city itself
   - user interests
   - that city's climate data
   - transport/travel data
   - hotel stay signals
   - budget estimate
6. Use raw climate data (per city) to generate practical climate-aware advice.
7. Use travel_sequence to describe the order attractions and cities should be visited in, and inter-city legs (distance/duration) where present.
8. Use hotel data (per city) only as accommodation guidance. If hotel POIs are missing for a city, suggest checking booking platforms for that city.
9. Budget estimate is rough. Make that clear.
10. If "feasible" is false, include a short, honest note that the requested days may be tight for the chosen cities, referencing replan_directives if present, without being alarmist.
11. Do not output HTML entities like &amp;.
12. Keep the response concise, polished, and useful.
13. Group the itinerary by city, in the order given by travel_sequence/selected_cities, with day numbers continuing across cities (do not restart at Day 1 for each city).

Structured planning context:
{json.dumps(payload, indent=2, ensure_ascii=False)}

Output format (Markdown):

## Trip Summary

## Climate-Aware Advice

## Travel Sequence

## Stay Suggestions

## Day-Wise Itinerary (grouped by city)

## Budget Snapshot

## Notes
"""
