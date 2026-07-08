import math
from typing import Any, Dict, Optional

import requests

from config.settings import api_settings, network_settings


class TransportService:
    def __init__(self):
        self.geoapify_api_key = api_settings.geoapify_api_key
        self.openrouteservice_api_key = api_settings.openrouteservice_api_key
        self.timeout = network_settings.request_timeout
        self.geoapify_ssl_verify = network_settings.geoapify_ssl_verify
        self.ssl_verify = network_settings.ssl_verify

        self.geoapify_geocode_url = "https://api.geoapify.com/v1/geocode/search"
        self.openrouteservice_directions_url = "https://api.openrouteservice.org/v2/directions"

    def get_transport_options(
        self,
        source: str,
        destination: str,
        mode: str = "driving-car",
    ) -> Dict[str, Any]:
        if not source:
            return {
                "success": False,
                "error": "Source is required for transport planning.",
                "transport": None,
            }

        if not destination:
            return {
                "success": False,
                "error": "Destination is required for transport planning.",
                "transport": None,
            }

        source_location = self._geocode_location(source)
        destination_location = self._geocode_location(destination)

        if not source_location:
            return {
                "success": False,
                "error": f"Could not geocode source: {source}",
                "transport": None,
            }

        if not destination_location:
            return {
                "success": False,
                "error": f"Could not geocode destination: {destination}",
                "transport": None,
            }

        route_data = self._get_openrouteservice_route(
            source_location=source_location,
            destination_location=destination_location,
            mode=mode,
        )

        if not route_data:
            route_data = self._build_fallback_route_estimate(
                source_location=source_location,
                destination_location=destination_location,
                mode=mode,
            )

        return {
            "success": True,
            "source": source,
            "destination": destination,
            "mode": mode,
            "source_location": source_location,
            "destination_location": destination_location,
            "transport": route_data,
        }

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
                verify=self.geoapify_ssl_verify,
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
                "query": location,
                "formatted": properties.get("formatted"),
                "city": properties.get("city") or properties.get("name"),
                "state": properties.get("state"),
                "country": properties.get("country"),
                "latitude": lat,
                "longitude": lon,
            }

        except Exception as e:
            print("[TransportService] Geoapify geocoding failed:")
            print(type(e).__name__, str(e))
            return None

    def _get_openrouteservice_route(
        self,
        source_location: Dict[str, Any],
        destination_location: Dict[str, Any],
        mode: str,
    ) -> Optional[Dict[str, Any]]:
        if not self.openrouteservice_api_key:
            return None

        source_lat = source_location.get("latitude")
        source_lon = source_location.get("longitude")
        dest_lat = destination_location.get("latitude")
        dest_lon = destination_location.get("longitude")

        if source_lat is None or source_lon is None or dest_lat is None or dest_lon is None:
            return None

        allowed_modes = {
            "driving-car",
            "driving-hgv",
            "cycling-regular",
            "foot-walking",
        }

        if mode not in allowed_modes:
            mode = "driving-car"

        url = f"{self.openrouteservice_directions_url}/{mode}/geojson"

        headers = {
            "Authorization": self.openrouteservice_api_key,
            "Content-Type": "application/json",
        }

        payload = {
            "coordinates": [
                [source_lon, source_lat],
                [dest_lon, dest_lat],
            ]
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
                verify=self.ssl_verify,
            )

            response.raise_for_status()
            data = response.json()

            features = data.get("features", [])

            if not features:
                return None

            properties = features[0].get("properties", {})
            summary = properties.get("summary", {})

            distance_meters = summary.get("distance")
            duration_seconds = summary.get("duration")

            distance_km = None
            duration_hours = None

            if distance_meters is not None:
                distance_km = round(distance_meters / 1000, 2)

            if duration_seconds is not None:
                duration_hours = round(duration_seconds / 3600, 2)

            return {
                "data_source": "openrouteservice",
                "route_mode": mode,
                "distance_km": distance_km,
                "duration_hours": duration_hours,
                "duration_minutes": round(duration_seconds / 60, 1) if duration_seconds else None,
                "distance_meters": distance_meters,
                "duration_seconds": duration_seconds,
                "route_summary": summary,
                "route_available": True,
            }

        except Exception as e:
            print("[TransportService] OpenRouteService route lookup failed:")
            print(type(e).__name__, str(e))
            return None

    def _build_fallback_route_estimate(
        self,
        source_location: Dict[str, Any],
        destination_location: Dict[str, Any],
        mode: str,
    ) -> Dict[str, Any]:
        source_lat = source_location.get("latitude")
        source_lon = source_location.get("longitude")
        dest_lat = destination_location.get("latitude")
        dest_lon = destination_location.get("longitude")

        distance_km = self._haversine_distance_km(
            source_lat,
            source_lon,
            dest_lat,
            dest_lon,
        )

        road_multiplier = 1.25
        estimated_road_distance = round(distance_km * road_multiplier, 2)

        average_speed_kmph = 50

        if mode == "driving-car":
            average_speed_kmph = 55
        elif mode == "cycling-regular":
            average_speed_kmph = 15
        elif mode == "foot-walking":
            average_speed_kmph = 5

        duration_hours = round(estimated_road_distance / average_speed_kmph, 2)

        return {
            "data_source": "fallback_haversine_estimate",
            "route_mode": mode,
            "distance_km": estimated_road_distance,
            "straight_line_distance_km": round(distance_km, 2),
            "duration_hours": duration_hours,
            "duration_minutes": round(duration_hours * 60, 1),
            "route_available": False,
            "note": (
                "OpenRouteService route was unavailable. "
                "This is an approximate distance estimate using coordinates."
            ),
        }

    def optimize_route(
        self,
        points: list,
        start_index: int = 0,
    ) -> Dict[str, Any]:
        """Order a list of points (attractions in a city, or cities in a trip)
        into a short visiting sequence using nearest-neighbour on straight-line
        distance. Deterministic, needs no external API.

        Each point must be a dict containing at least ``name``, ``latitude``
        and ``longitude``. Points missing coordinates are dropped.
        """
        usable_points = [
            point
            for point in points
            if isinstance(point, dict)
            and point.get("latitude") is not None
            and point.get("longitude") is not None
        ]

        if not usable_points:
            return {
                "success": False,
                "error": "No points with usable coordinates were provided.",
                "ordered_points": [],
                "legs": [],
                "total_distance_km": 0.0,
            }

        start_index = start_index if 0 <= start_index < len(usable_points) else 0

        remaining = list(usable_points)
        current = remaining.pop(start_index)
        ordered = [current]

        while remaining:
            nearest_index = min(
                range(len(remaining)),
                key=lambda i: self._haversine_distance_km(
                    current.get("latitude"),
                    current.get("longitude"),
                    remaining[i].get("latitude"),
                    remaining[i].get("longitude"),
                ),
            )

            current = remaining.pop(nearest_index)
            ordered.append(current)

        legs = []
        total_distance_km = 0.0

        for previous_point, next_point in zip(ordered, ordered[1:]):
            distance_km = round(
                self._haversine_distance_km(
                    previous_point.get("latitude"),
                    previous_point.get("longitude"),
                    next_point.get("latitude"),
                    next_point.get("longitude"),
                ),
                2,
            )

            legs.append(
                {
                    "from": previous_point.get("name"),
                    "to": next_point.get("name"),
                    "distance_km": distance_km,
                }
            )

            total_distance_km += distance_km

        return {
            "success": True,
            "ordered_points": ordered,
            "legs": legs,
            "total_distance_km": round(total_distance_km, 2),
        }

    def _haversine_distance_km(
        self,
        lat1: Optional[float],
        lon1: Optional[float],
        lat2: Optional[float],
        lon2: Optional[float],
    ) -> float:
        if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
            return 0.0

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