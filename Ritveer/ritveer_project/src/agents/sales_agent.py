from typing import Any, Dict, List
from src.graph.state import RitveerState
from config.settings import settings
from src.tools.google_maps_tools import search_places, book_kiosk
from src.tools.pwa_tools import generate_pwa_microstore

def sales_agent_node(state: RitveerState) -> Dict[str, Any]:
    """
    The SalesAgent node is responsible for sales-related activities,
    such as finding kiosk locations and generating PWA micro-stores.
    """
    print("---SALES AGENT: Initiating sales activities---")
    
    # Example: Get a normalized request from the state
    normalized_request = state.get("normalized_request", {})
    sales_task = normalized_request.get("sales_task", "")
    location = normalized_request.get("location", "")
    item = normalized_request.get("item", "")

    sales_outcome = {}

    if "find kiosk" in sales_task.lower() and location:
        print(f"SALES AGENT: Searching for kiosks near {location}")
        # Assuming a default query for kiosks and a radius
        places_results = search_places(query="kiosk", location=location, radius=5000)
        
        if places_results.get("status") == "failed":
            sales_outcome = {"status": "failed", "reason": places_results.get("message", "Kiosk search failed.")}
        else:
            # Process results, maybe pick the first one
            if places_results.get("results"):
                first_kiosk = places_results["results"][0]
                sales_outcome = {
                    "status": "kiosk_found",
                    "kiosk_name": first_kiosk.get("name"),
                    "kiosk_address": first_kiosk.get("formatted_address"),
                    "place_id": first_kiosk.get("place_id")
                }
                print(f"SALES AGENT: Found kiosk: {first_kiosk.get("name")}")
                
                # Simulate booking the kiosk
                booking_details = {"date": "2025-12-25", "duration": "1 day"}
                booking_result = book_kiosk(first_kiosk.get("place_id"), booking_details)
                if booking_result.get("status") == "success":
                    sales_outcome["booking_status"] = "success"
                    sales_outcome["booking_id"] = booking_result.get("booking_id")
                    print(f"SALES AGENT: Kiosk booked: {booking_result.get("booking_id")}")
                else:
                    sales_outcome["booking_status"] = "failed"
                    sales_outcome["booking_reason"] = booking_result.get("message")
                    print(f"SALES AGENT: Kiosk booking failed: {booking_result.get("message")}")
            else:
                sales_outcome = {"status": "no_kiosk_found", "reason": "No kiosks found near the specified location."}

    elif "create micro-store" in sales_task.lower() and item:
        print(f"SALES AGENT: Generating micro-store for item: {item}")
        # Assuming store name is derived from the item and location
        store_name = f"{item.replace(' ', '')}Store"
        products_list = [item] # For simplicity, just the requested item
        
        pwa_result = generate_pwa_microstore(store_name=store_name, location=location, products=products_list)
        
        if pwa_result.get("status") == "success":
            sales_outcome = {
                "status": "micro_store_created",
                "store_name": store_name,
                "store_url": pwa_result.get("url")
            }
            print(f"SALES AGENT: Micro-store created: {pwa_result.get("url")}")
        else:
            sales_outcome = {"status": "failed", "reason": pwa_result.get("message", "Micro-store creation failed.")}
    else:
        sales_outcome = {"status": "no_sales_task", "reason": "No recognized sales task in the request."}

    return {"sales_agent_outcome": sales_outcome}
