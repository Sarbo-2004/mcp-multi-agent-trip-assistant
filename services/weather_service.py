from datetime import datetime
from typing import Any, Dict, Optional

import requests

from config.settings import api_settings, network_settings


class WeatherService:
    def __init__(self):
        self.geoapify_api_key = api_settings.geoapify_api_key
        self.timeout = network_settings.request_timeout
        self.ssl_verify = network_settings.ssl_verify

        self.geoapify_geocode_url = "https://api.geoapify.com/v1/geocode/search"
        self.open_meteo_forecast_url = "https://api.open-meteo.com/v1/forecast"
        self.open_meteo_elevation_url = "https://api.open-meteo.com/v1/elevation"

    def get_climate(
        self,
        destination: str,
        month: Optional[str] = None,
        travel_dates: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        if not destination:
            return {
                "success": False,
                "error": "Destination is required for climate analysis.",
                "climate": None,
            }

        geo_data = self._geocode_location(destination)

        if not geo_data:
            return {
                "success": False,
                "error": f"Could not geocode destination: {destination}",
                "climate": None,
            }

        elevation_meters = self._get_elevation(
            latitude=geo_data.get("latitude"),
            longitude=geo_data.get("longitude"),
        )

        geo_data["elevation_meters"] = elevation_meters

        climate_data = None

        if travel_dates:
            climate_data = self._get_forecast_if_possible(
                latitude=geo_data.get("latitude"),
                longitude=geo_data.get("longitude"),
                elevation_meters=elevation_meters,
                travel_dates=travel_dates,
            )

        if not climate_data:
            climate_data = self._get_monthly_climate_indicators(
                destination=destination,
                month=month,
                geo_data=geo_data,
            )

        return {
            "success": True,
            "destination": destination,
            "month": month,
            "travel_dates": travel_dates,
            "location": geo_data,
            "climate": climate_data,
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
                "latitude": lat,
                "longitude": lon,
            }

        except Exception as e:
            print("[WeatherService] Geoapify geocoding failed:")
            print(type(e).__name__, str(e))
            return None

    def _get_elevation(
        self,
        latitude: Optional[float],
        longitude: Optional[float],
    ) -> Optional:
        if latitude is None or longitude is None:
            return None

        params = {
            "latitude": latitude,
            "longitude": longitude,
        }

        try:
            response = requests.get(
                self.open_meteo_elevation_url,
                params=params,
                timeout=self.timeout,
                verify=self.ssl_verify,
            )

            response.raise_for_status()
            data = response.json()

            elevation_values = data.get("elevation", [])

            if isinstance(elevation_values, list) and elevation_values:
                return elevation_values[0]

            if isinstance(elevation_values, (int, float)):
                return elevation_values

            return None

        except Exception as e:
            print("[WeatherService] Elevation lookup failed:")
            print(type(e).__name__, str(e))
            return None

    def _get_forecast_if_possible(
        self,
        latitude: Optional[float],
        longitude: Optional[float],
        elevation_meters: Optional[float],
        travel_dates: Dict[str, str],
    ) -> Optional[Dict[str, Any]]:
        if latitude is None or longitude is None:
            return None

        start_date = travel_dates.get("start_date")
        end_date = travel_dates.get("end_date")

        if not start_date or not end_date:
            return None

        try:
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")
        except Exception:
            return None

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_probability_max",
                "precipitation_sum",
            ],
            "timezone": "auto",
        }

        try:
            response = requests.get(
                self.open_meteo_forecast_url,
                params=params,
                timeout=self.timeout,
                verify=self.ssl_verify,
            )

            response.raise_for_status()
            data = response.json()
            daily = data.get("daily", {})

            max_temps = daily.get("temperature_2m_max", [])
            min_temps = daily.get("temperature_2m_min", [])
            rain_probs = daily.get("precipitation_probability_max", [])
            rain_sums = daily.get("precipitation_sum", [])

            if not max_temps or not min_temps:
                return None

            avg_max = round(sum(max_temps) / len(max_temps), 1)
            avg_min = round(sum(min_temps) / len(min_temps), 1)

            avg_rain_probability = None
            total_rain_mm = None

            if rain_probs:
                avg_rain_probability = round(sum(rain_probs) / len(rain_probs), 1)

            if rain_sums:
                total_rain_mm = round(sum(rain_sums), 1)

            return {
                "data_source": "open_meteo_forecast",
                "forecast_type": "date_specific",
                "temperature_celsius": {
                    "average_min": avg_min,
                    "average_max": avg_max,
                    "daily_min_values": min_temps,
                    "daily_max_values": max_temps,
                },
                "precipitation": {
                    "average_probability_percent": avg_rain_probability,
                    "total_rainfall_mm": total_rain_mm,
                    "daily_probability_values": rain_probs,
                    "daily_rainfall_values": rain_sums,
                },
                "terrain_indicators": {
                    "elevation_meters": elevation_meters,
                    "terrain_type": self._infer_terrain_type(elevation_meters),
                },
                "raw_daily_data": daily,
                "climate_flags": self._build_flags(
                    min_temp=avg_min,
                    max_temp=avg_max,
                    rain_probability=avg_rain_probability,
                    rainfall_mm=total_rain_mm,
                    month=None,
                    latitude=latitude,
                    longitude=longitude,
                    elevation_meters=elevation_meters,
                ),
            }

        except Exception as e:
            print("[WeatherService] Open-Meteo forecast failed:")
            print(type(e).__name__, str(e))
            return None

    def _get_monthly_climate_indicators(
        self,
        destination: str,
        month: Optional[str],
        geo_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        month_name = (month or "").strip().lower()
        latitude = geo_data.get("latitude")
        longitude = geo_data.get("longitude")
        elevation_meters = geo_data.get("elevation_meters")

        seasonal_band = self._infer_seasonal_band(month_name)

        terrain_type = self._infer_terrain_type(elevation_meters)

        region_type = self._infer_region_type(
            latitude=latitude,
            longitude=longitude,
            elevation_meters=elevation_meters,
        )

        estimated_temp = self._estimate_temperature_range(
            month=month_name,
            region_type=region_type,
            latitude=latitude,
            elevation_meters=elevation_meters,
        )

        rainfall_level = self._estimate_rainfall_level(
            month=month_name,
            region_type=region_type,
            elevation_meters=elevation_meters,
        )

        humidity_level = self._estimate_humidity_level(
            month=month_name,
            region_type=region_type,
            elevation_meters=elevation_meters,
        )

        return {
            "data_source": "seasonal_indicator_profile",
            "forecast_type": "month_level_estimate",
            "destination": destination,
            "month": month,
            "seasonal_band": seasonal_band,
            "geo_indicators": {
                "latitude": latitude,
                "longitude": longitude,
                "elevation_meters": elevation_meters,
            },
            "terrain_type": terrain_type,
            "region_type": region_type,
            "temperature_celsius": estimated_temp,
            "rainfall_level": rainfall_level,
            "humidity_level": humidity_level,
            "climate_flags": self._build_flags(
                min_temp=estimated_temp.get("estimated_min"),
                max_temp=estimated_temp.get("estimated_max"),
                rain_probability=None,
                rainfall_mm=None,
                month=month_name,
                latitude=latitude,
                longitude=longitude,
                elevation_meters=elevation_meters,
            ),
            "note": (
                "This is raw structured seasonal climate data, not a live weather forecast. "
                "Final travel advice should be generated by the final response composer."
            ),
        }

    def _infer_seasonal_band(self, month: str) -> str:
        if month in ["december", "january", "february"]:
            return "winter"

        if month in ["march", "april", "may"]:
            return "summer"

        if month in ["june", "july", "august", "september"]:
            return "monsoon"

        if month in ["october", "november"]:
            return "post_monsoon"

        return "unknown"

    def _infer_terrain_type(self, elevation_meters: Optional[float]) -> str:
        if elevation_meters is None:
            return "unknown"

        if elevation_meters >= 1500:
            return "highland"

        if elevation_meters >= 800:
            return "elevated_plateau_or_hill"

        if elevation_meters >= 300:
            return "plateau_or_inland"

        return "lowland"

    def _infer_region_type(
        self,
        latitude: Optional[float],
        longitude: Optional[float],
        elevation_meters: Optional[float],
    ) -> str:
        if elevation_meters is not None:
            if elevation_meters >= 1500:
                return "highland"
            if elevation_meters >= 800:
                return "elevated_plateau_or_hill"

        if latitude is None or longitude is None:
            return "general_india"

        if latitude >= 28:
            return "northern_region"

        if 23 <= latitude <= 29 and 68 <= longitude <= 77:
            return "dry_western_region"

        if 20 <= latitude <= 27 and longitude >= 80:
            return "eastern_humid_region"

        if 8 <= latitude <= 23 and longitude >= 72:
            return "peninsular_region"

        return "general_india"

    def _estimate_temperature_range(
        self,
        month: str,
        region_type: str,
        latitude: Optional[float],
        elevation_meters: Optional[float] = None,
    ) -> Dict[str, Any]:
        season = self._infer_seasonal_band(month)

        if elevation_meters is not None and elevation_meters >= 1500:
            if season == "winter":
                return {"estimated_min": 6, "estimated_max": 22}
            if season == "summer":
                return {"estimated_min": 12, "estimated_max": 26}
            if season == "monsoon":
                return {"estimated_min": 13, "estimated_max": 24}
            return {"estimated_min": 10, "estimated_max": 24}

        if elevation_meters is not None and elevation_meters >= 800:
            if season == "winter":
                return {"estimated_min": 10, "estimated_max": 25}
            if season == "summer":
                return {"estimated_min": 18, "estimated_max": 32}
            if season == "monsoon":
                return {"estimated_min": 18, "estimated_max": 28}
            return {"estimated_min": 15, "estimated_max": 30}

        if region_type == "dry_western_region":
            if season == "summer":
                return {"estimated_min": 26, "estimated_max": 42}
            if season == "winter":
                return {"estimated_min": 8, "estimated_max": 26}
            return {"estimated_min": 18, "estimated_max": 35}

        if region_type in ["eastern_humid_region", "peninsular_region"]:
            if season == "winter":
                return {"estimated_min": 20, "estimated_max": 31}
            if season == "summer":
                return {"estimated_min": 26, "estimated_max": 36}
            if season == "monsoon":
                return {"estimated_min": 25, "estimated_max": 34}
            return {"estimated_min": 23, "estimated_max": 33}

        if season == "winter":
            return {"estimated_min": 12, "estimated_max": 28}

        if season == "summer":
            return {"estimated_min": 25, "estimated_max": 40}

        if season == "monsoon":
            return {"estimated_min": 24, "estimated_max": 33}

        return {"estimated_min": 18, "estimated_max": 32}

    def _estimate_rainfall_level(
        self,
        month: str,
        region_type: str,
        elevation_meters: Optional[float] = None,
    ) -> str:
        season = self._infer_seasonal_band(month)

        if season == "monsoon":
            if region_type in [
                "peninsular_region",
                "eastern_humid_region",
                "highland",
                "elevated_plateau_or_hill",
            ]:
                return "high"

            return "medium"

        if season == "post_monsoon":
            if region_type in ["peninsular_region", "eastern_humid_region"]:
                return "medium"

        if season == "winter":
            return "low"

        if season == "summer":
            if region_type in ["peninsular_region", "eastern_humid_region"]:
                return "medium"

            return "low"

        return "medium"

    def _estimate_humidity_level(
        self,
        month: str,
        region_type: str,
        elevation_meters: Optional[float] = None,
    ) -> str:
        season = self._infer_seasonal_band(month)

        if region_type in ["peninsular_region", "eastern_humid_region"]:
            if season in ["summer", "monsoon", "post_monsoon"]:
                return "high"

            return "medium"

        if region_type == "dry_western_region":
            return "low"

        if season == "monsoon":
            return "high"

        return "medium"

    def _build_flags(
        self,
        min_temp: Optional[float],
        max_temp: Optional[float],
        rain_probability: Optional[float],
        rainfall_mm: Optional[float],
        month: Optional[str],
        latitude: Optional[float],
        longitude: Optional[float],
        elevation_meters: Optional[float] = None,
    ) -> Dict[str, Any]:
        monsoon_month = month in ["june", "july", "august", "september"]

        extreme_heat = False
        cold_nights = False
        rain_risk = False
        high_elevation = False

        if elevation_meters is not None and elevation_meters >= 1500:
            high_elevation = True

        if max_temp is not None and max_temp >= 36:
            extreme_heat = True

        if min_temp is not None and min_temp <= 12:
            cold_nights = True

        if rain_probability is not None and rain_probability >= 50:
            rain_risk = True

        if rainfall_mm is not None and rainfall_mm >= 20:
            rain_risk = True

        if monsoon_month:
            rain_risk = True

        return {
            "monsoon_month": monsoon_month,
            "extreme_heat": extreme_heat,
            "cold_nights": cold_nights,
            "rain_risk": rain_risk,
            "high_elevation": high_elevation,
            "latitude": latitude,
            "longitude": longitude,
            "elevation_meters": elevation_meters,
        }