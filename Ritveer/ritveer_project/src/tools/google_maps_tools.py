import requests
from typing import Dict, Any
from config.settings import settings


def search_places(query: str, location: str, radius: int = 5000) -> Dict[str, Any]:
    """Search for places using the Google Maps Places API."""
    print(f"GOOGLE MAPS TOOL: Searching for places with query '{query}' near '{location}' within {radius} meters.")
    api_key = settings.GOOGLE_MAPS_API_KEY
    if not api_key:
        return {"status": "failed", "message": "Google Maps API Key not configured."}
    base_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {"query": query, "location": location, "radius": radius, "key": api_key}
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"GOOGLE MAPS TOOL: Error searching places: {e}")
        return {"status": "failed", "message": f"Google Maps API error: {str(e)}"}


def geocode_address(address: str) -> Dict[str, Any]:
    """Geocode a human readable address into latitude and longitude."""
    print(f"GOOGLE MAPS TOOL: Geocoding address '{address}'.")
    api_key = settings.GOOGLE_MAPS_API_KEY
    if not api_key:
        return {"status": "failed", "message": "Google Maps API Key not configured."}
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": api_key}
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"GOOGLE MAPS TOOL: Error geocoding address: {e}")
        return {"status": "failed", "message": f"Google Maps API error: {str(e)}"}


def book_kiosk(place_id: str, booking_details: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate booking a kiosk at a given place_id."""
    print(f"GOOGLE MAPS TOOL: Simulating booking kiosk at place ID '{place_id}' with details: {booking_details}")
    return {"status": "success", "message": f"Kiosk at {place_id} booked successfully (simulated).", "booking_id": "BOOK" + place_id[:5].upper() + "123"}
