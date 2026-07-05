import html
import json
from typing import Any, Dict, List, Optional

import google.generativeai as genai
import requests

from config.settings import api_settings, network_settings


class PlacesService:
    def __init__(self):
        self.geoapify_api_key = api_settings.geoapify_api_key
        self.gemini_api_key = api_settings.gemini_api_key
        self.timeout = network_settings.request_timeout
        self.ssl_verify = network_settings.ssl_verify

        self.geoapify_geocode_url = "https://api.geoapify.com/v1/geocode/search"
        self.geoapify_places_url = "https://api.geoapify.com/v2/places"

        self.gemini_model = None

        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_model = genai.GenerativeModel("gemini-2.5-flash")

    def recommend_destinations(
        self,
        source: Optional[str] = None,
        interests: Optional[List[str]] = None,
        month: Optional[str] = None,
        budget: Optional[str] = None,
        days: Optional[int] = None,
        travelers: Optional[int] = None,
        limit: int = 8,
    ) -> Dict[str, Any]:
        interests = interests or []

        if not self.gemini_model:
            return {
                "success": False,
                "error": "Gemini API key is missing. Destination recommendation requires Gemini.",
                "recommendations": [],
            }

        candidates = self._generate_destination_candidates(
            source=source,
            interests=interests,
            month=month,
            budget=budget,
            days=days,
            travelers=travelers,
            limit=limit,
        )

        if not candidates:
            return {
                "success": False,
                "error": "No destination candidates generated.",
                "recommendations": [],
            }

        validated = []

        for candidate in candidates:
            destination_name = self._clean_destination_name(candidate.get("destination"))

            if not destination_name:
                continue

            geo_data = self._geocode_location(destination_name)

            if not geo_data:
                continue

            validated.append(
                {
                    "destination": destination_name,
                    "state_or_region": candidate.get("state_or_region"),
                    "country": geo_data.get("country"),
                    "formatted_address": geo_data.get("formatted"),
                    "latitude": geo_data.get("lat"),
                    "longitude": geo_data.get("lon"),
                    "match_score": candidate.get("match_score"),
                    "best_for": candidate.get("best_for", []),
                    "reason": candidate.get("reason"),
                    "ideal_days": candidate.get("ideal_days"),
                    "budget_fit": candidate.get("budget_fit"),
                    "travel_note": candidate.get("travel_note"),
                    "source": source,
                    "month": month,
                    "budget": budget,
                    "days": days,
                    "travelers": travelers,
                }
            )

        if not validated:
            return {
                "success": False,
                "error": "Destination candidates were generated but could not be validated using Geoapify.",
                "source": source,
                "interests": interests,
                "month": month,
                "budget": budget,
                "days": days,
                "travelers": travelers,
                "recommendations": [],
            }

        return {
            "success": True,
            "source": source,
            "interests": interests,
            "month": month,
            "budget": budget,
            "days": days,
            "travelers": travelers,
            "recommendations": validated[:limit],
        }

    def get_popular_places(
        self,
        destination: str,
        interests: Optional[List[str]] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        interests = interests or []

        if not destination:
            return {
                "success": False,
                "error": "Destination is required.",
                "places": [],
            }

        geo_data = self._geocode_location(destination)

        if not geo_data:
            return {
                "success": False,
                "error": f"Could not geocode destination: {destination}",
                "places": [],
            }

        lat = geo_data.get("lat")
        lon = geo_data.get("lon")

        categories = self._map_interests_to_geoapify_categories(interests)

        places = self._fetch_places_near_location(
            lat=lat,
            lon=lon,
            categories=categories,
            limit=limit,
        )

        return {
            "success": True,
            "destination": destination,
            "formatted_address": geo_data.get("formatted"),
            "latitude": lat,
            "longitude": lon,
            "interests": interests,
            "places": places,
        }

    def _generate_destination_candidates(
        self,
        source: Optional[str],
        interests: List[str],
        month: Optional[str],
        budget: Optional[str],
        days: Optional[int],
        travelers: Optional[int],
        limit: int,
    ) -> List[Dict[str, Any]]:
        prompt = f"""
You are a travel destination recommendation engine for India-focused trip planning.

Return only valid JSON.
Do not include markdown.
Do not explain anything.

User trip preferences:
- source city: {source}
- interests: {interests}
- month: {month}
- budget: {budget}
- days: {days}
- travelers: {travelers}

Task:
Recommend suitable Indian travel destinations.

Rules:
1. Prefer destinations realistically reachable from the source city.
2. Match interests such as beach, nature, food, nightlife, heritage, religious, adventure, shopping, relaxation, romantic.
3. Consider budget fit.
4. Consider trip duration.
5. Recommend popular and practical destinations.
6. Do not recommend obscure or low-tourism places unless user explicitly asks for offbeat places.
7. Do not invent non-existent destinations.
8. match_score must be between 0 and 100.
9. Return at most {limit} destinations.
10. Destination names should be clean city/place names, not combined labels.
11. For Andaman, use "Port Blair" as destination.
12. For Ooty and Coonoor, prefer "Ooty" as destination.
13. For Coorg, prefer "Madikeri" as destination.
14. For Alleppey, prefer "Alappuzha" as destination.

Return JSON exactly in this structure:
{{
  "recommendations": [
    {{
      "destination": "Destination Name",
      "state_or_region": "State or Region",
      "match_score": 90,
      "best_for": ["nature", "relaxation"],
      "reason": "Short explanation of why this destination matches.",
      "ideal_days": "3-5 days",
      "budget_fit": "low|medium|high|low-medium|medium-high",
      "travel_note": "Short note about reachability from source."
    }}
  ]
}}
"""

        try:
            response = self.gemini_model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.2,
                    "top_p": 0.8,
                    "top_k": 40,
                },
            )

            text = getattr(response, "text", "").strip()

            if not text:
                return []

            json_text = self._extract_json(text)
            data = json.loads(json_text)

            recommendations = data.get("recommendations", [])

            if not isinstance(recommendations, list):
                return []

            return recommendations[:limit]

        except Exception as e:
            print("[PlacesService] Gemini destination generation failed:")
            print(type(e).__name__, str(e))
            return []

    def _geocode_location(self, location: str) -> Optional[Dict[str, Any]]:
        if not self.geoapify_api_key:
            return None

        params = {
            "text": location,
            "apiKey": self.geoapify_api_key,
            "limit": 1,
            "filter": "countrycode:in",
        }

        try:
            response = requests.get(
                self.geoapify_geocode_url,
                params=params,
                timeout=self.timeout,
                verify=self.ssl_verify,
            )

            response.raise_for_status()
            data = response.json()

            features = data.get("features", [])

            if not features:
                return None

            properties = features[0].get("properties", {})
            geometry = features[0].get("geometry", {})
            coordinates = geometry.get("coordinates", [])

            lon = None
            lat = None

            if len(coordinates) >= 2:
                lon = coordinates[0]
                lat = coordinates[1]

            return {
                "formatted": properties.get("formatted"),
                "city": properties.get("city") or properties.get("name"),
                "state": properties.get("state"),
                "country": properties.get("country"),
                "lat": lat,
                "lon": lon,
                "raw": properties,
            }

        except Exception as e:
            print("[PlacesService] Geoapify geocoding failed:")
            print(type(e).__name__, str(e))
            return None

    def _fetch_places_near_location(
        self,
        lat: float,
        lon: float,
        categories: List[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        if not self.geoapify_api_key:
            return []

        if lat is None or lon is None:
            return []

        if not categories:
            categories = [
                "tourism.sights",
                "tourism.attraction",
                "leisure",
                "catering.restaurant",
            ]

        params = {
            "categories": ",".join(categories),
            "filter": f"circle:{lon},{lat},25000",
            "bias": f"proximity:{lon},{lat}",
            "limit": limit,
            "apiKey": self.geoapify_api_key,
        }

        try:
            response = requests.get(
                self.geoapify_places_url,
                params=params,
                timeout=self.timeout,
                verify=self.ssl_verify,
            )

            response.raise_for_status()
            data = response.json()

            places = []

            for feature in data.get("features", []):
                properties = feature.get("properties", {})
                geometry = feature.get("geometry", {})
                coordinates = geometry.get("coordinates", [])

                place_lon = None
                place_lat = None

                if len(coordinates) >= 2:
                    place_lon = coordinates[0]
                    place_lat = coordinates[1]

                name = (
                    properties.get("name")
                    or properties.get("address_line1")
                    or properties.get("formatted")
                )

                if not name:
                    continue

                places.append(
                    {
                        "name": name,
                        "category": properties.get("categories", []),
                        "formatted_address": properties.get("formatted"),
                        "latitude": place_lat,
                        "longitude": place_lon,
                        "distance_meters": properties.get("distance"),
                        "place_id": properties.get("place_id"),
                    }
                )

            return places[:limit]

        except Exception as e:
            print("[PlacesService] Geoapify places lookup failed:")
            print(type(e).__name__, str(e))
            return []

    def _map_interests_to_geoapify_categories(self, interests: List[str]) -> List:
        category_map = {
            "beach": [
                "beach",
                "tourism.attraction",
                "leisure",
            ],
            "nature": [
                "natural",
                "natural.forest",
                "tourism.attraction",
            ],
            "food": [
                "catering.restaurant",
                "catering.cafe",
                "commercial.food_and_drink",
            ],
            "nightlife": [
                "entertainment",
                "catering.bar",
                "catering.pub",
            ],
            "heritage": [
                "heritage",
                "tourism.sights",
                "tourism.museum",
                "building.historic",
            ],
            "religious": [
                "religion",
                "building.place_of_worship",
            ],
            "adventure": [
                "sport",
                "tourism.attraction",
                "leisure",
            ],
            "shopping": [
                "commercial",
                "commercial.shopping_mall",
                "commercial.marketplace",
            ],
            "relaxation": [
                "leisure",
                "tourism.attraction",
                "natural",
            ],
            "romantic": [
                "tourism.attraction",
                "leisure",
                "natural",
            ],
        }

        categories = []

        for interest in interests:
            mapped = category_map.get(interest, [])
            categories.extend(mapped)

        if not categories:
            categories = [
                "tourism.sights",
                "tourism.attraction",
                "leisure",
                "catering.restaurant",
            ]

        unique_categories = []

        for category in categories:
            if category not in unique_categories:
                unique_categories.append(category)

        return unique_categories

    def _clean_destination_name(self, destination: Optional[str]) -> Optional:
        if not destination:
            return None

        destination = html.unescape(destination).strip()

        cleanup_map = {
            "Alleppey (Alappuzha)": "Alappuzha",
            "Coorg (Madikeri)": "Madikeri",
            "Ooty & Coonoor": "Ooty",
            "Andaman & Nicobar Islands": "Port Blair",
        }

        return cleanup_map.get(destination, destination)

    def _extract_json(self, text: str) -> str:
        text = text.strip()

        if text.startswith("```json"):
            text = text.replace("```json", "").replace("```", "").strip()

        elif text.startswith("```"):
            text = text.replace("```", "").strip()

        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1:
            return text[start:end + 1]

        return text