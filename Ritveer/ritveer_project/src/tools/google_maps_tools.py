import requests
from typing import Dict, Any, List
from config.settings import settings

def search_places(query: str, location: str, radius: int = 5000) -> Dict[str, Any]:
    """
    Searches for places using the Google Maps Places API.

    Args:
        query: The text search string (e.g., "kiosk").
        location: The latitude and longitude around which to retrieve place information (e.g., "34.0522,-118.2437").
        radius: Defines the distance (in meters) within which to return place results. The maximum allowed radius is 50,000 meters.

    Returns:
        A dictionary containing the search results from Google Maps Places API.
    """
    print(f"GOOGLE MAPS TOOL: Searching for places with query '{query}' near '{location}' within {radius} meters.")
    
    api_key = settings.GOOGLE_MAPS_API_KEY
    if not api_key:
        return {"status": "failed", "message": "Google Maps API Key not configured."}

    base_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": query,
        "location": location,
        "radius": radius,
        "key": api_key
    }

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"GOOGLE MAPS TOOL: Error searching places: {e}")
        return {"status": "failed", "message": f"Google Maps API error: {str(e)}"}

def book_kiosk(place_id: str, booking_details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulates booking a kiosk at a given place_id.
    In a real scenario, this would involve interaction with a booking system.

    Args:
        place_id: The Google Place ID of the kiosk location.
        booking_details: A dictionary containing booking-specific information (e.g., date, time, duration).

    Returns:
        A dictionary indicating the success or failure of the booking.
    """
    print(f"GOOGLE MAPS TOOL: Simulating booking kiosk at place ID '{place_id}' with details: {booking_details}")
    # Simulate a successful booking for now
    return {"status": "success", "message": f"Kiosk at {place_id} booked successfully (simulated).", "booking_id": "BOOK" + place_id[:5].upper() + "123"}
