import html
import json
from typing import Any, Dict, List, Optional

import google.generativeai as genai
import requests

from config.constants import (
    SCOPE_CITY,
    SCOPE_STATE,
    SCOPE_COUNTRY,
    SCOPE_REGION,
    SCOPE_UNKNOWN,
)
from config.settings import api_settings, network_settings


# ---------------------------------------------------------------------- #
# Geoapify destination scope constants
# ---------------------------------------------------------------------- #

CITY_RESULT_TYPES = {
    "city",
    "town",
    "village",
    "suburb",
    "district",
    "municipality",
}

STATE_RESULT_TYPES = {
    "state",
    "county",
    "province",
}

COUNTRY_RESULT_TYPES = {
    "country",
}

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


# ---------------------------------------------------------------------- #
# POI filtering constants
# ---------------------------------------------------------------------- #

STRONG_ATTRACTION_CATEGORY_TERMS = [
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


BLOCKED_POI_CATEGORY_TERMS = [
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


BLOCKED_POI_NAME_HINTS = [
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


class PlacesService:
    def __init__(self):
        self.geoapify_api_key = api_settings.geoapify_api_key
        self.gemini_api_key = api_settings.gemini_api_key
        self.timeout = network_settings.request_timeout
        self.ssl_verify = network_settings.geoapify_ssl_verify

        self.geoapify_geocode_url = "https://api.geoapify.com/v1/geocode/search"
        self.geoapify_places_url = "https://api.geoapify.com/v2/places"

        self.gemini_model = None
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_model = genai.GenerativeModel(api_settings.gemini_model)

    # ------------------------------------------------------------------ #
    # Destination recommendation when user has no fixed destination
    # ------------------------------------------------------------------ #

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
                "error": "Gemini API key is required to recommend destinations from preference-only queries.",
                "recommendations": [],
            }

        prompt = f"""
You are a destination recommendation engine for an Indian trip planning assistant.

Return only valid JSON.
Do not include markdown.
Do not explain anything.

Task:
Recommend suitable Indian city/town destinations for the user's trip preferences.

Rules:
1. Recommend concrete Indian cities/towns only.
2. Do not recommend broad states/regions/countries.
3. Do not recommend attractions, hotels, restaurants, cafes, roads, or markets as destinations.
4. Prefer practical destinations based on source, month, interests, budget, days, and travelers.
5. Each recommendation must include a short reason and match_score from 0 to 100.
6. Return at most {limit} destinations.

Input:
source: {source}
interests: {json.dumps(interests, ensure_ascii=False)}
month: {month}
budget: {budget}
days: {days}
travelers: {travelers}

Return JSON exactly in this format:
{{
  "recommendations": [
    {{
      "destination": "City Name",
      "state": "State Name",
      "reason": "short reason",
      "match_score": 85,
      "best_for": ["heritage", "food"],
      "budget_fit": "low|medium|high"
    }}
  ]
}}
"""

        try:
            response = self.gemini_model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.25,
                    "top_p": 0.8,
                    "top_k": 40,
                },
            )

            text = getattr(response, "text", "").strip()
            data = json.loads(self._extract_json(text))

            recommendations = data.get("recommendations", [])
            validated = self._validate_recommendation_candidates(
                recommendations=recommendations,
                limit=limit,
            )

            return {
                "success": True,
                "source": source,
                "interests": interests,
                "month": month,
                "budget": budget,
                "days": days,
                "travelers": travelers,
                "recommendations": validated,
                "recommendation_method": "gemini_validated_by_geoapify",
            }

        except Exception as e:
            print("[PlacesService] Destination recommendation failed:")
            print(type(e).__name__, str(e))
            return {
                "success": False,
                "error": f"Destination recommendation failed: {type(e).__name__}: {str(e)}",
                "recommendations": [],
            }

    # ------------------------------------------------------------------ #
    # Destination scope classification
    # ------------------------------------------------------------------ #

    def classify_destination(self, name: str) -> Dict[str, Any]:
        if not name:
            return {
                "success": False,
                "error": "Destination name is required for classification.",
                "scope": SCOPE_UNKNOWN,
            }

        normalized_name = self._clean_text(name)
        if not normalized_name:
            return {
                "success": False,
                "error": "Destination name is empty after cleanup.",
                "scope": SCOPE_UNKNOWN,
            }

        lowered = normalized_name.lower()

        if any(keyword == lowered for keyword in KNOWN_REGION_KEYWORDS):
            return {
                "success": True,
                "input": name,
                "canonical_name": normalized_name.title(),
                "scope": SCOPE_REGION,
                "classification_method": "known_region_keyword",
            }

        geo_data = self._geocode_location(normalized_name)

        if not geo_data:
            return {
                "success": False,
                "error": f"Could not classify destination: {name}",
                "scope": SCOPE_UNKNOWN,
            }

        result_type = str(geo_data.get("result_type") or "").lower()
        canonical_name = (
            geo_data.get("city")
            or geo_data.get("state")
            or geo_data.get("country")
            or geo_data.get("name")
            or normalized_name
        )

        if result_type in CITY_RESULT_TYPES:
            scope = SCOPE_CITY
        elif result_type in STATE_RESULT_TYPES:
            scope = SCOPE_STATE
        elif result_type in COUNTRY_RESULT_TYPES:
            scope = SCOPE_COUNTRY
        else:
            scope = self._fallback_scope_from_geocode(geo_data)

        return {
            "success": True,
            "input": name,
            "canonical_name": canonical_name,
            "scope": scope,
            "result_type": result_type,
            "location": geo_data,
            "classification_method": "geoapify_geocode",
        }

    def _fallback_scope_from_geocode(self, geo_data: Dict[str, Any]) -> str:
        if geo_data.get("city"):
            return SCOPE_CITY

        if geo_data.get("state") and not geo_data.get("city"):
            return SCOPE_STATE

        if geo_data.get("country") and not geo_data.get("city") and not geo_data.get("state"):
            return SCOPE_COUNTRY

        return SCOPE_UNKNOWN

    # ------------------------------------------------------------------ #
    # City recommendations inside state/region/country
    # ------------------------------------------------------------------ #

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
        interests = interests or []

        if not region:
            return {
                "success": False,
                "error": "Region is required to recommend cities.",
                "recommendations": [],
            }

        if not self.gemini_model:
            return {
                "success": False,
                "error": "Gemini API key is required to recommend cities inside a broad region.",
                "recommendations": [],
            }

        prompt = f"""
You are a city selection planner for an Indian trip planning assistant.

Return only valid JSON.
Do not include markdown.
Do not explain anything.

Task:
Recommend concrete cities/towns inside the given broad destination/region.

Rules:
1. Recommend city/town names only.
2. Do not recommend the broad region itself.
3. Do not recommend attractions, restaurants, hotels, roads, or markets as cities.
4. Consider trip duration, interests, budget, travelers, and travel style.
5. Prefer realistic combinations for the number of days.
6. Return at most {limit} cities.

Input:
region: {region}
interests: {json.dumps(interests, ensure_ascii=False)}
days: {days}
budget: {budget}
travelers: {travelers}
travel_style: {travel_style}

Return JSON exactly in this format:
{{
  "recommendations": [
    {{
      "destination": "City Name",
      "state": "State Name",
      "reason": "short reason",
      "match_score": 90,
      "best_for": ["heritage", "food"]
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
            data = json.loads(self._extract_json(text))

            recommendations = data.get("recommendations", [])
            validated = self._validate_city_candidates_inside_region(
                region=region,
                recommendations=recommendations,
                limit=limit,
            )

            return {
                "success": True,
                "region": region,
                "interests": interests,
                "days": days,
                "budget": budget,
                "travelers": travelers,
                "travel_style": travel_style,
                "recommendations": validated,
                "recommendation_method": "gemini_validated_by_geoapify",
            }

        except Exception as e:
            print("[PlacesService] City recommendation inside region failed:")
            print(type(e).__name__, str(e))
            return {
                "success": False,
                "error": f"City recommendation failed: {type(e).__name__}: {str(e)}",
                "recommendations": [],
            }

    # ------------------------------------------------------------------ #
    # Popular places / attractions
    # ------------------------------------------------------------------ #

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
                "error": "Destination is required for places lookup.",
                "places": [],
            }

        geo_data = self._geocode_location(destination)

        if not geo_data:
            return {
                "success": False,
                "error": f"Could not geocode destination: {destination}",
                "places": [],
            }

        categories = self._build_attraction_categories(interests)

        raw_places = self._fetch_geoapify_places(
            latitude=geo_data.get("latitude"),
            longitude=geo_data.get("longitude"),
            categories=categories,
            limit=max(limit * 4, 30),
        )

        usable_places = self._filter_usable_attractions(raw_places)

        landmark_fallback_used = False
        landmark_candidates = []
        validated_landmarks = []

        if len(usable_places) < 3:
            landmark_fallback_used = True
            landmark_candidates = self._generate_landmark_candidates(
                city=destination,
                interests=interests,
                limit=max(limit, 8),
            )
            validated_landmarks = self._validate_landmark_candidates(
                city=destination,
                city_location=geo_data,
                candidates=landmark_candidates,
                limit=limit,
            )
            usable_places = self._merge_places(
                primary=usable_places,
                secondary=validated_landmarks,
                limit=limit,
            )

        usable_places = usable_places[:limit]

        return {
            "success": True,
            "destination": destination,
            "location": geo_data,
            "interests": interests,
            "categories_used": categories,
            "places": usable_places,
            "raw_place_count": len(raw_places),
            "usable_place_count": len(usable_places),
            "poi_quality": "usable" if len(usable_places) >= 3 else "weak",
            "landmark_fallback_used": landmark_fallback_used,
            "landmark_candidates": landmark_candidates,
            "validated_landmark_count": len(validated_landmarks),
            "note": (
                "Strong sightseeing POIs are returned. Restaurants, cafes, hotels, roads, shops, "
                "bookstores, and commercial POIs are filtered out. If normal Geoapify POIs are weak, "
                "canonical landmark candidates are generated by Gemini and validated with Geoapify."
            ),
        }

    def _build_attraction_categories(self, interests: Optional[List[str]]) -> List:
        interests = interests or []

        base_categories = [
            "tourism",
            "tourism.attraction",
            "tourism.sights",
            "tourism.information",
            "entertainment.museum",
            "natural",
            "natural.water",
            "natural.beach",
            "leisure.park",
            "religion",
        ]

        interest_category_map = {
            "heritage": [
                "tourism.sights",
                "tourism.attraction",
                "entertainment.museum",
            ],
            "religious": [
                "religion",
                "tourism.sights",
            ],
            "nature": [
                "natural",
                "natural.water",
                "natural.forest",
                "natural.mountain",
                "leisure.park",
            ],
            "beach": [
                "natural.beach",
                "natural.water",
                "tourism.attraction",
            ],
            "adventure": [
                "natural",
                "sport",
                "tourism.attraction",
            ],
            "shopping": [
                "tourism.sights",
            ],
            "food": [
                "tourism.sights",
                "tourism.attraction",
            ],
            "nightlife": [
                "tourism.sights",
                "tourism.attraction",
            ],
            "relaxation": [
                "natural",
                "leisure.park",
                "tourism.attraction",
            ],
            "romantic": [
                "natural",
                "natural.water",
                "tourism.attraction",
                "tourism.sights",
            ],
        }

        categories = list(base_categories)

        for interest in interests:
            categories.extend(interest_category_map.get(str(interest).lower(), []))

        seen = set()
        unique_categories = []

        for category in categories:
            if category not in seen:
                seen.add(category)
                unique_categories.append(category)

        return unique_categories

    def _fetch_geoapify_places(
        self,
        latitude: Optional[float],
        longitude: Optional[float],
        categories: List[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        if not self.geoapify_api_key:
            return []

        if latitude is None or longitude is None:
            return []

        params = {
            "categories": ",".join(categories),
            "filter": f"circle:{longitude},{latitude},25000",
            "bias": f"proximity:{longitude},{latitude}",
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

                lon = None
                lat = None

                if len(coordinates) >= 2:
                    lon = coordinates[0]
                    lat = coordinates[1]

                name = (
                    properties.get("name")
                    or properties.get("address_line1")
                    or properties.get("formatted")
                )

                if not name:
                    continue

                places.append(
                    {
                        "name": self._clean_text(name),
                        "categories": properties.get("categories", []),
                        "formatted_address": self._clean_text(properties.get("formatted")),
                        "latitude": lat,
                        "longitude": lon,
                        "distance_meters": properties.get("distance"),
                        "place_id": properties.get("place_id"),
                        "source": "geoapify_places",
                    }
                )

            return places

        except Exception as e:
            print("[PlacesService] Geoapify places lookup failed:")
            print(type(e).__name__, str(e))
            return []

    def _filter_usable_attractions(self, places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not places:
            return []

        filtered = []
        seen_names = set()

        for place in places:
            if not isinstance(place, dict):
                continue

            name = self._clean_text(place.get("name"))

            if not name:
                continue

            normalized_name = name.lower().strip()

            if normalized_name in seen_names:
                continue

            if self._looks_like_blocked_poi_name(normalized_name):
                continue

            categories = (
                place.get("categories")
                or place.get("category")
                or place.get("kinds")
                or []
            )

            if isinstance(categories, str):
                categories = [categories]

            category_text = " ".join(str(category).lower() for category in categories)

            if self._has_blocked_poi_category(category_text):
                continue

            if not self._has_strong_attraction_category(category_text):
                continue

            cleaned_place = {
                "name": name,
                "categories": categories,
                "formatted_address": self._clean_text(place.get("formatted_address")),
                "latitude": place.get("latitude"),
                "longitude": place.get("longitude"),
                "distance_meters": place.get("distance_meters"),
                "place_id": place.get("place_id"),
                "source": place.get("source") or "geoapify",
            }

            filtered.append(cleaned_place)
            seen_names.add(normalized_name)

        return filtered

    # ------------------------------------------------------------------ #
    # Landmark fallback: Gemini candidates + Geoapify validation
    # ------------------------------------------------------------------ #

    def _generate_landmark_candidates(
        self,
        city: str,
        interests: Optional[List[str]],
        limit: int = 8,
    ) -> List[Dict[str, Any]]:
        interests = interests or []

        if not self.gemini_model:
            return []

        prompt = f"""
You are a canonical attraction candidate generator for an Indian travel planning system.

Return only valid JSON.
Do not include markdown.
Do not explain anything.

Task:
List well-known sightseeing attractions for the given Indian city.

Rules:
1. Return only attractions/landmarks suitable for a travel itinerary.
2. Do not return restaurants, cafes, hotels, roads, streets, shops, bookstores, offices, banks, or generic markets.
3. Prefer forts, palaces, temples, museums, lakes, gardens, viewpoints, monuments, heritage sites, and nature spots.
4. Do not invent obscure or fake places.
5. Keep names concise and searchable.
6. Match user interests where possible.
7. Return at most {limit} candidates.

City:
{city}

User interests:
{json.dumps(interests, ensure_ascii=False)}

Return JSON exactly in this format:
{{
  "candidates": [
    {{
      "name": "Attraction Name",
      "type": "fort|palace|museum|lake|temple|garden|viewpoint|monument|heritage|nature|other",
      "reason": "short reason"
    }}
  ]
}}
"""

        try:
            response = self.gemini_model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.15,
                    "top_p": 0.8,
                    "top_k": 40,
                },
            )

            text = getattr(response, "text", "").strip()
            data = json.loads(self._extract_json(text))

            candidates = data.get("candidates", [])
            cleaned = []

            for item in candidates:
                if not isinstance(item, dict):
                    continue

                name = self._clean_text(item.get("name"))
                if not name:
                    continue

                normalized_name = name.lower()
                if self._looks_like_blocked_poi_name(normalized_name):
                    continue

                cleaned.append(
                    {
                        "name": name,
                        "type": self._clean_text(item.get("type")) or "attraction",
                        "reason": self._clean_text(item.get("reason")),
                        "source": "gemini_landmark_candidate",
                    }
                )

                if len(cleaned) >= limit:
                    break

            return cleaned

        except Exception as e:
            print("[PlacesService] Landmark candidate generation failed:")
            print(type(e).__name__, str(e))
            return []

    def _validate_landmark_candidates(
    self,
    city: str,
    city_location: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    limit: int,
) -> List[Dict[str, Any]]:
        if not candidates:
            return []
    
        validated = []
        seen_names = set()
    
        city_name = self._clean_text(city)
        city_name_lower = city_name.lower() if city_name else ""
    
        city_lat = city_location.get("latitude")
        city_lon = city_location.get("longitude")
    
        for candidate in candidates:
            name = self._clean_text(candidate.get("name"))
    
            if not name:
                continue
            
            normalized_name = name.lower().strip()
    
            if normalized_name in seen_names:
                continue
            
            if self._looks_like_blocked_poi_name(normalized_name):
                continue
            
            query = f"{name}, {city}, India"
            geo_data = self._geocode_location(query)
    
            if not geo_data:
                continue
            
            lat = geo_data.get("latitude")
            lon = geo_data.get("longitude")
    
            if lat is None or lon is None:
                continue
            
            resolved_city = self._clean_text(
                geo_data.get("city")
                or geo_data.get("town")
                or geo_data.get("village")
                or geo_data.get("name")
            )
    
            resolved_city_lower = resolved_city.lower() if resolved_city else ""
    
            distance_km = None
    
            if city_lat is not None and city_lon is not None:
                distance_km = self._haversine_km(
                    lat1=float(city_lat),
                    lon1=float(city_lon),
                    lat2=float(lat),
                    lon2=float(lon),
                )
    
            candidate_type = str(candidate.get("type") or "").lower()
    
            # Strict city ownership guard:
            # If Geoapify clearly resolves this landmark to another selected city/town,
            # do not attach it to the current city.
            if resolved_city_lower and city_name_lower:
                if resolved_city_lower != city_name_lower:
                    # Allow only broad natural/outing spots within a reasonable excursion radius.
                    is_excursion_type = any(
                        term in candidate_type
                        for term in ["lake", "beach", "nature", "wildlife", "waterfall"]
                    )
    
                    if not is_excursion_type:
                        continue
                    
            # Normal city landmark radius.
            # This prevents "Konark Sun Temple" from being added to Puri.
            # Natural excursions get a slightly larger radius.
            if distance_km is not None:
                is_excursion_type = any(
                    term in candidate_type
                    for term in ["lake", "beach", "nature", "wildlife", "waterfall"]
                )
    
                max_radius_km = 55 if is_excursion_type else 30
    
                if distance_km > max_radius_km:
                    continue
                
            validated_place = {
                "name": name,
                "categories": [
                    "tourism.attraction",
                    "validated_landmark",
                    str(candidate.get("type") or "attraction"),
                ],
                "formatted_address": geo_data.get("formatted"),
                "latitude": lat,
                "longitude": lon,
                "distance_meters": int(distance_km * 1000) if distance_km is not None else None,
                "place_id": geo_data.get("place_id"),
                "reason": candidate.get("reason"),
                "source": "gemini_candidate_geoapify_validated",
                "resolved_city": resolved_city,
            }
    
            if self._filter_usable_attractions([validated_place]):
                validated.append(validated_place)
                seen_names.add(normalized_name)
    
            if len(validated) >= limit:
                break
            
        return validated
    
    def _merge_places(
        self,
        primary: List[Dict[str, Any]],
        secondary: List[Dict[str, Any]],
        limit: int,
    ) -> List[Dict[str, Any]]:
        merged = []
        seen_names = set()

        for place in list(primary or []) + list(secondary or []):
            if not isinstance(place, dict):
                continue

            name = self._clean_text(place.get("name"))

            if not name:
                continue

            normalized_name = name.lower().strip()

            if normalized_name in seen_names:
                continue

            merged.append(place)
            seen_names.add(normalized_name)

            if len(merged) >= limit:
                break

        return merged

    # ------------------------------------------------------------------ #
    # Place ranking
    # ------------------------------------------------------------------ #

    def rank_places(
        self,
        city: str,
        places: List[Dict[str, Any]],
        interests: Optional[List[str]] = None,
        days: Optional[int] = None,
    ) -> Dict[str, Any]:
        interests = interests or []
        places = places or []

        usable_places = self._filter_usable_attractions(places)

        if not usable_places:
            return {
                "success": True,
                "city": city,
                "interests": interests,
                "days": days,
                "ranked_places": [],
                "poi_quality": "weak",
                "note": (
                    "No reliable sightseeing POIs were available after filtering. "
                    "The final composer should create a high-level itinerary without naming raw POIs."
                ),
            }

        if not self.gemini_model:
            return {
                "success": True,
                "city": city,
                "interests": interests,
                "days": days,
                "ranked_places": usable_places,
                "poi_quality": "usable" if len(usable_places) >= 3 else "weak",
                "ranking_method": "filtered_order_without_llm",
            }

        prompt = f"""
You are ranking sightseeing attractions for a travel itinerary.

Return only valid JSON.
Do not include markdown.
Do not add new places.

Rules:
1. Use only the provided places.
2. Rank genuine sightseeing attractions higher.
3. Prefer places that match the user's interests.
4. Do not rank restaurants, cafes, hotels, shops, roads, offices, banks, streets, or commercial places.
5. Do not invent famous attractions missing from the provided list.

City:
{city}

Interests:
{json.dumps(interests, ensure_ascii=False)}

Days:
{days}

Places:
{json.dumps(usable_places, indent=2, ensure_ascii=False)}

Return JSON exactly in this format:
{{
  "ranked_places": [
    {{
      "name": "place name",
      "reason": "short reason",
      "priority": 1
    }}
  ]
}}
"""

        try:
            response = self.gemini_model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.1,
                    "top_p": 0.8,
                    "top_k": 40,
                },
            )

            text = getattr(response, "text", "").strip()
            data = json.loads(self._extract_json(text))

            ranked_names = [
                item.get("name")
                for item in data.get("ranked_places", [])
                if item.get("name")
            ]

            places_by_name = {
                str(place.get("name")).lower(): place
                for place in usable_places
                if place.get("name")
            }

            ranked_places = []

            for name in ranked_names:
                matched = places_by_name.get(str(name).lower())
                if matched:
                    ranked_places.append(matched)

            ranked_existing_names = {
                str(place.get("name")).lower()
                for place in ranked_places
                if place.get("name")
            }

            for place in usable_places:
                place_name = str(place.get("name")).lower()
                if place_name not in ranked_existing_names:
                    ranked_places.append(place)

            return {
                "success": True,
                "city": city,
                "interests": interests,
                "days": days,
                "ranked_places": ranked_places,
                "poi_quality": "usable" if len(ranked_places) >= 3 else "weak",
                "ranking_method": "gemini_filtered_ranking",
            }

        except Exception as e:
            print("[PlacesService] Gemini place ranking failed:")
            print(type(e).__name__, str(e))

            return {
                "success": True,
                "city": city,
                "interests": interests,
                "days": days,
                "ranked_places": usable_places,
                "poi_quality": "usable" if len(usable_places) >= 3 else "weak",
                "ranking_method": "fallback_filtered_order",
                "ranking_error": str(e),
            }

    # ------------------------------------------------------------------ #
    # Recommendation validation helpers
    # ------------------------------------------------------------------ #

    def _validate_recommendation_candidates(
        self,
        recommendations: List[Dict[str, Any]],
        limit: int,
    ) -> List[Dict[str, Any]]:
        validated = []
        seen = set()

        for item in recommendations:
            if not isinstance(item, dict):
                continue

            destination = self._clean_text(item.get("destination"))
            if not destination:
                continue

            normalized_destination = destination.lower()

            if normalized_destination in seen:
                continue

            geo_data = self._geocode_location(destination)

            if not geo_data:
                continue

            scope = self._fallback_scope_from_geocode(geo_data)

            if scope != SCOPE_CITY:
                continue

            city = geo_data.get("city") or destination
            state = geo_data.get("state") or item.get("state")

            validated.append(
                {
                    "destination": city,
                    "state": state,
                    "reason": self._clean_text(item.get("reason")),
                    "match_score": item.get("match_score"),
                    "best_for": item.get("best_for") or [],
                    "budget_fit": item.get("budget_fit"),
                    "location": geo_data,
                }
            )

            seen.add(normalized_destination)

            if len(validated) >= limit:
                break

        return validated

    def _validate_city_candidates_inside_region(
        self,
        region: str,
        recommendations: List[Dict[str, Any]],
        limit: int,
    ) -> List[Dict[str, Any]]:
        validated = []
        seen = set()
        region_lower = region.lower().strip()

        for item in recommendations:
            if not isinstance(item, dict):
                continue

            destination = self._clean_text(item.get("destination"))

            if not destination:
                continue

            normalized_destination = destination.lower().strip()

            if normalized_destination == region_lower:
                continue

            if normalized_destination in seen:
                continue

            geo_data = self._geocode_location(destination)

            if not geo_data:
                continue

            scope = self._fallback_scope_from_geocode(geo_data)

            if scope != SCOPE_CITY:
                continue

            city = geo_data.get("city") or destination
            state = geo_data.get("state") or item.get("state")

            validated.append(
                {
                    "destination": city,
                    "state": state,
                    "reason": self._clean_text(item.get("reason")),
                    "match_score": item.get("match_score"),
                    "best_for": item.get("best_for") or [],
                    "location": geo_data,
                }
            )

            seen.add(normalized_destination)

            if len(validated) >= limit:
                break

        return validated

    # ------------------------------------------------------------------ #
    # Geoapify helpers
    # ------------------------------------------------------------------ #

    def _geocode_location(self, location: str) -> Optional[Dict[str, Any]]:
        if not self.geoapify_api_key:
            return None

        location = self._clean_text(location)

        if not location:
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
                "name": properties.get("name"),
                "city": properties.get("city")
                or properties.get("town")
                or properties.get("village"),
                "state": properties.get("state"),
                "country": properties.get("country"),
                "result_type": properties.get("result_type"),
                "latitude": lat,
                "longitude": lon,
                "place_id": properties.get("place_id"),
            }

        except Exception as e:
            print("[PlacesService] Geoapify geocoding failed:")
            print(type(e).__name__, str(e))
            return None

    # ------------------------------------------------------------------ #
    # POI quality helpers
    # ------------------------------------------------------------------ #

    def _has_strong_attraction_category(self, category_text: str) -> bool:
        if not category_text:
            return False

        return any(term in category_text for term in STRONG_ATTRACTION_CATEGORY_TERMS)

    def _has_blocked_poi_category(self, category_text: str) -> bool:
        if not category_text:
            return False

        return any(term in category_text for term in BLOCKED_POI_CATEGORY_TERMS)

    def _looks_like_blocked_poi_name(self, normalized_name: str) -> bool:
        if not normalized_name:
            return True

        return any(hint in normalized_name for hint in BLOCKED_POI_NAME_HINTS)

    # ------------------------------------------------------------------ #
    # Numeric helpers
    # ------------------------------------------------------------------ #

    def _haversine_km(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        import math

        radius_km = 6371.0

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return radius_km * c

    # ------------------------------------------------------------------ #
    # Generic helpers
    # ------------------------------------------------------------------ #

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

    def _clean_text(self, value: Any) -> Optional:
        if value is None:
            return None

        if not isinstance(value, str):
            value = str(value)

        value = html.unescape(value)
        value = " ".join(value.split())
        value = value.strip()

        return value or None