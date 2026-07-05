import html
import json
from typing import Any, Dict, List, Optional

import google.generativeai as genai
import requests

from config.constants import SCOPE_CITY, SCOPE_STATE, SCOPE_COUNTRY, SCOPE_REGION, SCOPE_UNKNOWN
from config.settings import api_settings, network_settings


# Geoapify `result_type` values that unambiguously identify a single city/town.
CITY_RESULT_TYPES = {"city", "town", "village", "suburb", "district", "municipality"}
# Geoapify `result_type` values that identify a state/province-level area.
STATE_RESULT_TYPES = {"state", "county", "province"}
COUNTRY_RESULT_TYPES = {"country"}

# Colloquial multi-state regions that Geoapify cannot geocode to a single
# administrative boundary (e.g. "South India", "North East"). These are
# recognized up front so classification does not depend on a weak geocode match.
KNOWN_REGION_KEYWORDS = [
    "south india",
    "north india",
    "north east india",
    "north east",
    "northeast",
    "east india",
    "west india",
    "central india",
]


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
            self.gemini_model = genai.GenerativeModel("gemini-flash-lite-latest")

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

    def classify_destination(self, name: str) -> Dict[str, Any]:
        """Classify a destination name as a city, state, region or country.

        Deterministic path: geocode via Geoapify and read its ``result_type``.
        Falls back to Gemini only when geocoding fails or is ambiguous (e.g.
        colloquial multi-state regions like "South India" that have no single
        administrative boundary).
        """
        if not name:
            return {
                "success": False,
                "error": "Destination name is required.",
                "scope": SCOPE_UNKNOWN,
            }

        normalized = name.strip().lower()

        if any(keyword in normalized for keyword in KNOWN_REGION_KEYWORDS):
            return {
                "success": True,
                "scope": SCOPE_REGION,
                "canonical_name": name.strip().title(),
                "source": "keyword_match",
            }

        geo_data = self._geocode_location(name)

        if not geo_data:
            return self._classify_destination_with_gemini(name)

        result_type = (geo_data.get("raw") or {}).get("result_type")
        scope = self._map_result_type_to_scope(result_type)

        if scope == SCOPE_UNKNOWN:
            gemini_result = self._classify_destination_with_gemini(name)

            if gemini_result.get("success"):
                gemini_result.setdefault("latitude", geo_data.get("lat"))
                gemini_result.setdefault("longitude", geo_data.get("lon"))
                return gemini_result

        return {
            "success": True,
            "scope": scope,
            "canonical_name": geo_data.get("city") or name.strip().title(),
            "state": geo_data.get("state"),
            "country": geo_data.get("country"),
            "latitude": geo_data.get("lat"),
            "longitude": geo_data.get("lon"),
            "source": "geoapify",
        }

    def _map_result_type_to_scope(self, result_type: Optional[str]) -> str:
        if not result_type:
            return SCOPE_UNKNOWN

        if result_type in CITY_RESULT_TYPES:
            return SCOPE_CITY

        if result_type in STATE_RESULT_TYPES:
            return SCOPE_STATE

        if result_type in COUNTRY_RESULT_TYPES:
            return SCOPE_COUNTRY

        return SCOPE_UNKNOWN

    def _classify_destination_with_gemini(self, name: str) -> Dict[str, Any]:
        if not self.gemini_model:
            return {
                "success": False,
                "error": "Could not classify destination and Gemini API key is missing.",
                "scope": SCOPE_UNKNOWN,
            }

        prompt = f"""
You are a geography classifier for India-focused trip planning.

Return only valid JSON. Do not include markdown. Do not explain anything.

Classify the following destination name into exactly one scope:
- "city": a specific city or town (e.g. Jaipur, Ooty, Goa town)
- "state": a single Indian state or union territory (e.g. Rajasthan, Kerala)
- "region": a multi-state colloquial region (e.g. South India, North East, Rajasthan-Gujarat circuit)
- "country": a whole country (e.g. India)

Destination: {name}

Return JSON exactly in this structure:
{{
  "scope": "city|state|region|country",
  "canonical_name": "Cleaned display name"
}}
"""

        try:
            response = self.gemini_model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.0,
                    "top_p": 0.8,
                    "top_k": 40,
                },
            )

            text = getattr(response, "text", "").strip()

            if not text:
                return {
                    "success": False,
                    "error": "Gemini returned an empty destination classification.",
                    "scope": SCOPE_UNKNOWN,
                }

            data = json.loads(self._extract_json(text))
            scope = data.get("scope")

            if scope not in {SCOPE_CITY, SCOPE_STATE, SCOPE_REGION, SCOPE_COUNTRY}:
                scope = SCOPE_UNKNOWN

            return {
                "success": scope != SCOPE_UNKNOWN,
                "scope": scope,
                "canonical_name": data.get("canonical_name") or name.strip().title(),
                "source": "gemini",
            }

        except Exception as e:
            print("[PlacesService] Gemini destination classification failed:")
            print(type(e).__name__, str(e))
            return {
                "success": False,
                "error": f"Destination classification failed: {type(e).__name__}: {str(e)}",
                "scope": SCOPE_UNKNOWN,
            }

    def recommend_cities_in_region(
        self,
        region: str,
        interests: Optional[List[str]] = None,
        days: Optional[int] = None,
        budget: Optional[str] = None,
        travelers: Optional[int] = None,
        travel_style: Optional[str] = None,
        limit: int = 6,
    ) -> Dict[str, Any]:
        """Recommend candidate cities inside a broad state/region/country.

        Mirrors ``recommend_destinations`` (Gemini generates candidates,
        Geoapify validates each one) but scoped to cities *within* the given
        region rather than open-ended destinations across India.
        """
        interests = interests or []

        if not region:
            return {
                "success": False,
                "error": "Region is required.",
                "recommendations": [],
            }

        if not self.gemini_model:
            return {
                "success": False,
                "error": "Gemini API key is missing. City recommendation requires Gemini.",
                "recommendations": [],
            }

        candidates = self._generate_city_candidates(
            region=region,
            interests=interests,
            days=days,
            budget=budget,
            travelers=travelers,
            travel_style=travel_style,
            limit=limit,
        )

        if not candidates:
            return {
                "success": False,
                "error": f"No candidate cities generated for '{region}'.",
                "recommendations": [],
            }

        validated = []

        for candidate in candidates:
            city_name = self._clean_destination_name(candidate.get("city"))

            if not city_name:
                continue

            geo_data = self._geocode_location(city_name)

            if not geo_data:
                continue

            validated.append(
                {
                    "destination": city_name,
                    "state_or_region": region,
                    "country": geo_data.get("country"),
                    "formatted_address": geo_data.get("formatted"),
                    "latitude": geo_data.get("lat"),
                    "longitude": geo_data.get("lon"),
                    "match_score": candidate.get("match_score"),
                    "best_for": candidate.get("best_for", []),
                    "reason": candidate.get("reason"),
                    "ideal_days": candidate.get("ideal_days"),
                    "budget_fit": candidate.get("budget_fit"),
                }
            )

        if not validated:
            return {
                "success": False,
                "error": f"City candidates for '{region}' could not be validated using Geoapify.",
                "region": region,
                "recommendations": [],
            }

        return {
            "success": True,
            "region": region,
            "interests": interests,
            "days": days,
            "budget": budget,
            "travelers": travelers,
            "recommendations": validated[:limit],
        }

    def _generate_city_candidates(
        self,
        region: str,
        interests: List[str],
        days: Optional[int],
        budget: Optional[str],
        travelers: Optional[int],
        travel_style: Optional[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        prompt = f"""
You are a travel destination recommendation engine for India-focused trip planning.

Return only valid JSON.
Do not include markdown.
Do not explain anything.

The user wants to visit this broad state/region/country: {region}

User trip preferences:
- interests: {interests}
- days available: {days}
- budget: {budget}
- travelers: {travelers}
- travel style: {travel_style}

Task:
Recommend the best specific cities or towns to visit WITHIN "{region}" — do not
recommend places outside this state/region/country.

Rules:
1. Only recommend real, well-known tourist cities/towns located inside "{region}".
2. Match interests such as beach, nature, food, nightlife, heritage, religious, adventure, shopping, relaxation, romantic.
3. Consider the number of days available: recommend fewer cities for shorter trips.
4. Consider budget fit and travel style.
5. Do not invent non-existent places.
6. match_score must be between 0 and 100.
7. Return at most {limit} cities.
8. City names should be clean city/town names only.

Return JSON exactly in this structure:
{{
  "cities": [
    {{
      "city": "City Name",
      "match_score": 90,
      "best_for": ["heritage", "food"],
      "reason": "Short explanation of why this city matches.",
      "ideal_days": "2-3 days",
      "budget_fit": "low|medium|high|low-medium|medium-high"
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

            data = json.loads(self._extract_json(text))
            cities = data.get("cities", [])

            if not isinstance(cities, list):
                return []

            return cities[:limit]

        except Exception as e:
            print("[PlacesService] Gemini city recommendation failed:")
            print(type(e).__name__, str(e))
            return []

    def rank_places(
        self,
        city: str,
        places: List[Dict[str, Any]],
        interests: Optional[List[str]] = None,
        days: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Rank a single city's attractions using Gemini.

        Attractions are always fetched and ranked per city — never merged
        across cities — so this must be called once per selected city with
        that city's own place list.
        """
        interests = interests or []

        if not places:
            return {
                "success": True,
                "city": city,
                "ranked_places": [],
            }

        if not self.gemini_model:
            # Ranking is an enhancement, not a hard requirement: degrade
            # gracefully to the geoapify distance-sorted order instead of
            # failing the whole attractions step.
            return {
                "success": True,
                "city": city,
                "ranked_places": places,
                "note": "Gemini unavailable; returned distance-sorted order without ranking.",
            }

        compact_places = [
            {
                "name": place.get("name"),
                "category": place.get("category"),
                "distance_meters": place.get("distance_meters"),
            }
            for place in places
            if isinstance(place, dict)
        ]

        prompt = f"""
You are a travel attraction ranking engine.

Return only valid JSON. Do not include markdown. Do not explain anything.

City: {city}
User interests: {interests}
Days available in this city: {days}

Candidate attractions (JSON list):
{json.dumps(compact_places, ensure_ascii=False)}

Task:
Rank these attractions from most to least worth visiting for this specific
city, given the user's interests and days available. Do not add attractions
that are not in the candidate list. Do not invent attractions.

Return JSON exactly in this structure:
{{
  "ranked": [
    {{
      "name": "Attraction name from the candidate list",
      "rank": 1,
      "reason": "Short reason this attraction is worth visiting."
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
                return {
                    "success": True,
                    "city": city,
                    "ranked_places": places,
                    "note": "Gemini returned empty ranking; using distance-sorted order.",
                }

            data = json.loads(self._extract_json(text))
            ranked = data.get("ranked", [])

            if not isinstance(ranked, list) or not ranked:
                return {
                    "success": True,
                    "city": city,
                    "ranked_places": places,
                    "note": "Gemini ranking was empty; using distance-sorted order.",
                }

            places_by_name = {
                place.get("name"): place
                for place in places
                if isinstance(place, dict) and place.get("name")
            }

            ranked_places = []

            for entry in ranked:
                original = places_by_name.get(entry.get("name"))

                if not original:
                    continue

                ranked_places.append(
                    {
                        **original,
                        "rank": entry.get("rank"),
                        "rank_reason": entry.get("reason"),
                    }
                )

            if not ranked_places:
                ranked_places = places

            return {
                "success": True,
                "city": city,
                "ranked_places": ranked_places,
            }

        except Exception as e:
            print("[PlacesService] Gemini place ranking failed:")
            print(type(e).__name__, str(e))
            return {
                "success": True,
                "city": city,
                "ranked_places": places,
                "note": f"Ranking failed ({type(e).__name__}); using distance-sorted order.",
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