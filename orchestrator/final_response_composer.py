import html
import json
from dataclasses import asdict
from typing import Any, Dict, List

import google.generativeai as genai

from config.settings import api_settings
from schemas.trip_schema import TripContext


class FinalResponseComposer:
    def __init__(self):
        self.model = None

        if api_settings.gemini_api_key:
            genai.configure(api_key=api_settings.gemini_api_key)
            self.model = genai.GenerativeModel(api_settings.gemini_model)

    def compose(self, context: TripContext) -> Dict[str, Any]:
        if not self.model:
            return {
                "success": False,
                "error": "Gemini API key is missing. Final response composition skipped.",
                "response": None,
            }

        payload = self._build_payload(context)
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

    def _build_payload(self, context: TripContext) -> Dict[str, Any]:
        return {
            "request": asdict(context.request),
            "required_agents": context.required_agents,
            "agent_results": {
                agent_name: asdict(result)
                for agent_name, result in context.agent_results.items()
            },
            "errors": context.errors,
        }

    def _compact_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        request = payload.get("request", {})
        agent_results = payload.get("agent_results", {})

        destination_result = self._safe_get(
            agent_results,
            ["destination_agent", "data"],
        )

        climate_result = self._safe_get(
            agent_results,
            ["climate_agent", "data", "raw_climate_data"],
        )

        transport_result = self._safe_get(
            agent_results,
            ["transport_agent", "data", "raw_transport_data"],
        )

        hotel_result = self._safe_get(
            agent_results,
            ["hotel_agent", "data", "raw_hotel_data"],
        )

        itinerary_result = self._safe_get(
            agent_results,
            ["itinerary_agent", "data"],
        )

        budget_result = self._safe_get(
            agent_results,
            ["budget_agent", "data"],
        )

        compact_destination = self._compact_destination_result(destination_result)

        return {
            "request": request,
            "turn_type": request.get("turn_type"),
            "destination_scope": request.get("destination_scope", "unknown"),
            "destination_result": compact_destination,
            "climate_result": climate_result,
            "transport_result": transport_result,
            "hotel_result": hotel_result,
            "itinerary_result": itinerary_result,
            "budget_result": budget_result,
            "errors": payload.get("errors", []),
        }

    def _compact_destination_result(self, destination_result: Dict[str, Any]) -> Dict[str, Any]:
        if not destination_result:
            return {}

        mode = destination_result.get("mode")

        if mode == "destination_recommendation":
            recommendations_data = destination_result.get("recommended_destinations", {})
            recommendations = recommendations_data.get("recommendations", [])

            compact_recommendations = []

            for item in recommendations[:8]:
                compact_recommendations.append(
                    {
                        "destination": self._clean_text(item.get("destination")),
                        "state_or_region": self._clean_text(item.get("state_or_region")),
                        "match_score": item.get("match_score"),
                        "best_for": item.get("best_for"),
                        "reason": self._clean_text(item.get("reason")),
                        "ideal_days": self._clean_text(item.get("ideal_days")),
                        "budget_fit": self._clean_text(item.get("budget_fit")),
                        "travel_note": self._clean_text(item.get("travel_note")),
                    }
                )

            return {
                "mode": mode,
                "source": destination_result.get("source"),
                "interests": destination_result.get("interests"),
                "recommendations": compact_recommendations,
            }

        if mode == "places_lookup":
            places_data = destination_result.get("places", {})
            places = places_data.get("places", [])

            filtered_places = self._filter_high_quality_places(places)

            return {
                "mode": mode,
                "destination": destination_result.get("destination"),
                "interests": destination_result.get("interests"),
                "places_available": len(filtered_places) > 0,
                "poi_quality": "usable" if len(filtered_places) >= 3 else "weak",
                "places": filtered_places[:8],
                "raw_place_count": len(places),
                "filtered_place_count": len(filtered_places),
                "composer_instruction": (
                    "Use named POIs only if poi_quality is usable. "
                    "If poi_quality is weak, generate a high-level itinerary using destination, interests, climate, transport, hotel, and budget context."
                ),
            }

        return destination_result

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

Your job is to compose the final user-facing travel response using structured outputs from multiple agents.

Architecture rule:
- Agents provide raw facts.
- You generate final reasoning, advice, and itinerary.
- Do not expose internal JSON or agent names.

Critical destination-scope rules:
1. If destination_scope is "state_or_region", do NOT create a day-wise itinerary.
2. If destination_scope is "state_or_region", explain that the destination is broad and must be narrowed to a city, town, or route.
3. If destination_scope is "state_or_region", recommend specific city/circuit options using available destination recommendations if present.
4. If destination_scope is "state_or_region", ask the user to choose one option before climate, transport, hotel, or itinerary planning.
5. If destination_scope is "state_or_region", do not say "Day 1", "Day 2", or create a detailed itinerary.

General rules:
1. Do not invent exact transport numbers. Use transport data only if present.
2. Do not invent exact hotel names if hotel POIs are missing.
3. Do not blindly use restaurant, cafe, hotel, bank, street, statue, office, or random local POI names as main attractions.
4. If destination places have poi_quality = "weak", do not mention those POI names.
5. If POIs are weak, create a high-level itinerary based on:
   - destination
   - user interests
   - climate data
   - transport data
   - hotel stay signals
   - budget estimate
6. Use raw climate data to generate practical climate-aware advice.
7. Use raw transport data to explain route distance and travel duration.
8. Use hotel data only as accommodation guidance. If hotel POIs are missing, suggest checking booking platforms.
9. Budget estimate is rough. Make that clear.
10. Do not output HTML entities like &amp;.
11. Keep the response concise, polished, and useful.
12. If the itinerary cannot rely on strong POIs, use safe labels like beaches, old town/heritage areas, cafes, markets, viewpoints, nature spots, and relaxed local exploration without naming unsupported places.

Structured planning context:
{json.dumps(payload, indent=2, ensure_ascii=False)}

Output format:

If destination_scope is "state_or_region", return Markdown using this format:

## Trip Summary

## Why We Need to Narrow the Destination

## Recommended City or Route Options

## Budget Snapshot

## Next Step

If destination_scope is NOT "state_or_region", return Markdown using this format:

## Trip Summary

## Climate-Aware Advice

## Travel / Transport

## Stay Suggestions

## Day-Wise Itinerary

## Budget Snapshot

## Notes
"""