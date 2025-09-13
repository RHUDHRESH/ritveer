from typing import Any, Dict
from src.graph.state import RitveerState
from src.tools.shipping_tools import create_shiprocket_shipment, create_india_post_shipment

def ops_agent_node(state: RitveerState) -> Dict[str, Any]:
    """
    The ops agent node reads order details, calls the appropriate shipping tool,
    and updates the state with shipping label URL and tracking ID.
    """
    print("---OPS AGENT: Processing shipping and logistics---")
    final_order = state.get("final_order", {})
    normalized_request = state.get("normalized_request", {})

    if not final_order or final_order.get("status") != "committed":
        print("OPS AGENT: No committed order found. Skipping shipping.")
        return {"shipping_label_url": None, "tracking_id": None}

    # Determine which shipping tool to use (e.g., based on location, cost, policy)
    # For demonstration, let's use Shiprocket by default
    
    # Prepare order details for the shipping tool
    shipping_order_details = {
        "order_id": final_order.get("receipt_id"),
        "item_name": final_order.get("item"),
        "quantity": normalized_request.get("quantity"),
        "recipient_address": normalized_request.get("location"), # Assuming location is address
        "recipient_phone": normalized_request.get("sender_phone_number"), # Assuming sender is recipient
        "amount": final_order.get("price"),
        "currency": final_order.get("currency"),
    }

    shipping_result = create_shiprocket_shipment(shipping_order_details)
    
    if "error" not in shipping_result:
        print("OPS AGENT: Shipment created successfully.")
        return {
            "shipping_label_url": shipping_result.get("shipping_label_url"),
            "tracking_id": shipping_result.get("tracking_id"),
        }
    else:
        print(f"OPS AGENT: Failed to create shipment: {shipping_result['error']}")
        return {"shipping_label_url": None, "tracking_id": None}
