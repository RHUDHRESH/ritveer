from typing import Any, Dict
from src.graph.state import RitveerState
from src.tools.postgis_tools import find_artisan_clusters

def cluster_agent_node(state: RitveerState) -> Dict[str, Any]:
    """
    The cluster agent node reads the location from the normalized_request,
    finds artisan clusters, and updates the artisan_clusters in the state.
    """
    print("---CLUSTER AGENT: Finding artisan clusters---")
    normalized_request = state.get("normalized_request", {})
    
    location = normalized_request.get("location")
    item = normalized_request.get("item") # Assuming item can be used as craft_type
    
    if not location:
        print("CLUSTER AGENT: No location found in normalized_request. Skipping clustering.")
        return {"artisan_clusters": []}

    # Assuming location is a string that can be parsed into lat/lon or a known place
    # For now, let's assume location is a string like "latitude,longitude" or a city name
    # This needs to be more robust, potentially using a geocoding tool.
    # For demonstration, let's use a dummy lat/lon if location is just a city name.
    
    # Example: If location is "Bangalore", use a default lat/lon for Bangalore
    target_location = {"latitude": 12.9716, "longitude": 77.5946} # Default to Bangalore
    if isinstance(location, str) and "," in location:
        try:
            lat, lon = map(float, location.split(","))
            target_location = {"latitude": lat, "longitude": lon}
        except ValueError:
            pass # Use default if parsing fails

    # Call the find_artisan_clusters tool
    # Assuming 'item' can be mapped to 'craft_type' for filtering
    craft_type = item if item else None
    
    clusters = find_artisan_clusters(
        target_location=target_location,
        craft_type=craft_type
    )
    
    return {"artisan_clusters": clusters}