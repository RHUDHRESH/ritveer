from fastapi import APIRouter, HTTPException
from src.tools.google_maps_tools import search_places, geocode_address

router = APIRouter(prefix="/maps", tags=["maps"])


@router.get("/search")
def map_search(query: str, location: str, radius: int = 5000):
    """Search for places near a location using Google Maps."""
    result = search_places(query=query, location=location, radius=radius)
    if result.get("status") == "failed":
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result


@router.get("/geocode")
def map_geocode(address: str):
    """Geocode an address into latitude and longitude using Google Maps."""
    result = geocode_address(address)
    if result.get("status") == "failed":
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result
