from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from services.places_service import PlacesService


app = FastAPI(
    title="Places MCP HTTP Server",
    version="1.0.0",
)

places_service = PlacesService()


class PopularPlacesRequest(BaseModel):
    destination: str
    interests: Optional[List[str]] = []
    limit: int = 10


class RecommendDestinationsRequest(BaseModel):
    source: Optional[str] = None
    interests: Optional[List[str]] = []
    month: Optional[str] = None
    budget: Optional[str] = None
    days: Optional[int] = None
    travelers: Optional[int] = None
    limit: int = 8


@app.get("/health")
def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "server": "places_mcp_server",
    }


@app.post("/tools/get_popular_places")
def get_popular_places(request: PopularPlacesRequest) -> Dict[str, Any]:
    return places_service.get_popular_places(
        destination=request.destination,
        interests=request.interests,
        limit=request.limit,
    )


@app.post("/tools/recommend_destinations")
def recommend_destinations(request: RecommendDestinationsRequest) -> Dict[str, Any]:
    return places_service.recommend_destinations(
        source=request.source,
        interests=request.interests,
        month=request.month,
        budget=request.budget,
        days=request.days,
        travelers=request.travelers,
        limit=request.limit,
    )