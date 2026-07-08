import html
import json
import re
from typing import Any, Dict, List

import google.generativeai as genai

from config.settings import api_settings
from schemas.trip_schema import TripState


class FinalResponseComposer:
    """
    Turns a completed TripState into the final user-facing Markdown response.

    Important:
    - TransportAgent owns route/sequence construction.
    - Composer only renders the prepared travel_sequence/display_sequence.
    """

    STRONG_ATTRACTION_TERMS = [
        "tourism",
        "tourism.attraction",
        "tourism.sights",
        "tourism.information",
        "entertainment.museum",
        "museum",
        "heritage",
        "historic",
        "historical",
        "monument",
        "memorial",
        "castle",
        "fort",
        "palace",
        "archaeological",
        "religion",
        "temple",
        "church",
        "mosque",
        "natural",
        "natural.water",
        "natural.mountain",
        "natural.forest",
        "natural.beach",
        "beach",
        "lake",
        "waterfall",
        "park",
        "garden",
        "viewpoint",
        "zoo",
        "aquarium",
        "leisure.park",
        "validated_landmark",
    ]

    WEAK_OR_NON_ATTRACTION_TERMS = [
        "catering",
        "restaurant",
        "cafe",
        "coffee",
        "bar",
        "pub",
        "fast_food",
        "food_court",
        "accommodation",
        "hotel",
        "hostel",
        "guest_house",
        "apartment",
        "resort",
        "commercial",
        "shop",
        "shopping",
        "marketplace",
        "supermarket",
        "mall",
        "book",
        "books",
        "bookstore",
        "office",
        "bank",
        "atm",
        "street",
        "road",
        "highway",
        "residential",
        "building",
        "service",
        "healthcare",
        "hospital",
        "pharmacy",
        "education",
        "school",
        "college",
        "university",
        "parking",
        "fuel",
        "transport",
        "bus",
        "railway",
        "airport",
    ]

    WEAK_NAME_HINTS = [
        "road",
        "street",
        "rasta",
        "marg",
        "path",
        "lane",
        "hotel",
        "restaurant",
        "cafe",
        "coffee",
        "bhojnalaya",
        "dhaba",
        "bar",
        "pub",
        "book",
        "pustak",
        "store",
        "shop",
        "bank",
        "atm",
    ]

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
                    "temperature": 0.18,
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
                "response": self._clean_final_response(text),
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
            filtered_places = self._filter_high_quality_places(places)

            compact_cities[city] = {
                "places_available": len(filtered_places) > 0,
                "poi_quality": "usable" if len(filtered_places) >= 3 else "weak",
                "usable_place_count": len(filtered_places),
                "places": filtered_places[:8],
            }

        climate_by_city = self._safe_get(agent_results, ["climate_agent", "data", "by_city"]) or {}
        hotel_by_city = self._safe_get(agent_results, ["hotel_agent", "data", "by_city"]) or {}
        itinerary_result = self._safe_get(agent_results, ["itinerary_agent", "data"]) or {}
        budget_result = self._safe_get(agent_results, ["budget_agent", "data"]) or {}
        transport_result = self._safe_get(agent_results, ["transport_agent", "data"]) or {}

        compact_climate = {
            city: self._safe_get(result, ["data", "raw_climate_data"])
            for city, result in climate_by_city.items()
        }

        compact_hotel = {
            city: self._safe_get(result, ["data", "raw_hotel_data"])
            for city, result in hotel_by_city.items()
        }

        prepared_travel_sequence = payload.get("travel_sequence") or transport_result

        return {
            "request": request,
            "selected_cities": payload.get("selected_cities", []),
            "city_attractions": compact_cities,
            "climate_by_city": compact_climate,
            "hotel_by_city": compact_hotel,
            "travel_sequence": prepared_travel_sequence,
            "itinerary_skeleton": itinerary_result,
            "budget_result": budget_result,
            "feasible": payload.get("feasible"),
            "replan_directives": payload.get("replan_directives", []),
            "errors": payload.get("errors", []),
            "composer_instruction": (
                "Render travel_sequence.display_sequence exactly as the prepared route flow. "
                "Do not build route sequence yourself. Do not invent distances or local POI order."
            ),
        }

    def _filter_high_quality_places(self, places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not places:
            return []

        filtered = []
        seen_names = set()

        for item in places:
            if not isinstance(item, dict):
                continue

            name = self._clean_text(item.get("name"))

            if not name:
                continue

            normalized_name = name.lower().strip()

            if normalized_name in seen_names:
                continue

            if self._looks_like_weak_name(normalized_name):
                continue

            categories = (
                item.get("categories")
                or item.get("category")
                or item.get("kinds")
                or []
            )

            if isinstance(categories, str):
                categories = [categories]

            category_text = " ".join(str(category).lower() for category in categories)

            if self._has_weak_category(category_text):
                continue

            if not self._has_strong_attraction_category(category_text):
                continue

            seen_names.add(normalized_name)

            filtered.append(
                {
                    "name": name,
                    "categories": categories,
                    "formatted_address": self._clean_text(
                        item.get("formatted_address")
                        or item.get("address")
                        or item.get("formatted")
                    ),
                    "distance_meters": item.get("distance_meters") or item.get("distance"),
                    "latitude": item.get("latitude"),
                    "longitude": item.get("longitude"),
                    "source": item.get("source") or "places_service",
                }
            )

        return filtered

    def _has_strong_attraction_category(self, category_text: str) -> bool:
        if not category_text:
            return False

        return any(term in category_text for term in self.STRONG_ATTRACTION_TERMS)

    def _has_weak_category(self, category_text: str) -> bool:
        if not category_text:
            return False

        return any(term in category_text for term in self.WEAK_OR_NON_ATTRACTION_TERMS)

    def _looks_like_weak_name(self, normalized_name: str) -> bool:
        if not normalized_name:
            return True

        return any(hint in normalized_name for hint in self.WEAK_NAME_HINTS)

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

        value = html.unescape(value)
        value = re.sub(r"\s+", " ", value)
        return value.strip()

    def _clean_final_response(self, text: str) -> str:
        text = html.unescape(text)
        text = text.replace("\u00a0", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)

        text = re.sub(r"([a-z])It ", r"\1. It ", text)
        text = re.sub(r"([a-z])This ", r"\1. This ", text)
        text = re.sub(r"([a-z])Please ", r"\1. Please ", text)

        return text.strip()

    def _build_prompt(self, payload: Dict[str, Any]) -> str:
        return f"""
You are a professional AI trip planning assistant.

Your job:
Compose the final user-facing travel response using structured outputs from trip-planning components.

Architecture rules:
- Components provide raw facts.
- You generate the final written response.
- Do not expose internal JSON.
- Do not mention internal component names.
- Do not invent exact transport distances, hotel names, or attraction names.

CRITICAL TRAVEL SEQUENCE RULES:
1. Use travel_sequence.display_sequence as the source of truth.
2. Do not construct or infer route sequence yourself.
3. Do not invent missing distances or durations.
4. Render each transfer in display_sequence.
5. Render each city_flow in display_sequence.
6. If city_flow has poi_names, include those POIs as the local movement order.
7. If city_flow has no POIs, write a high-level local flow only.
8. For long transfers, mention that they should be treated as dedicated travel blocks.
9. Do not list only city-to-city transfers if city_flow data is available.

ATTRACTION RULES:
10. Use named attractions only from structured city_attractions or travel_sequence city_flow.
11. Never use restaurants, cafes, hotels, roads, streets, bookstores, shops, banks, offices, or random commercial POIs as attractions.
12. Do not invent famous attractions missing from the structured context.

CLIMATE RULES:
13. Use climate_by_city for practical advice.
14. Day-wise itinerary must reflect climate advice.
15. For hot or humid months, schedule outdoor visits early morning/evening and midday rest/indoor activities.

HOTEL RULES:
16. Use hotel_by_city for stay-area guidance.
17. Do not invent specific hotel names.
18. If hotel data is limited, suggest areas and stay types.

BUDGET RULES:
19. Budget is a rough estimate. Say that clearly.
20. If feasible is false, include a short feasibility warning.
21. If replan_directives exist, explain the adjustment naturally.

STYLE RULES:
22. Keep the answer polished, professional, concise, and useful.
23. Use Markdown.
24. Day numbers must continue across cities.
25. Do not output HTML entities like &amp;.
26. Do not include internal field names like poi_quality, raw_climate_data, or agent_results.

Structured planning context:
{json.dumps(payload, indent=2, ensure_ascii=False)}

Output format:

## Trip Summary

## Climate-Aware Advice

## Travel Sequence

## Stay Suggestions

## Day-Wise Itinerary

## Budget Snapshot

## Notes
"""