from typing import Any, Dict
from src.graph.state import RitveerState
from src.tools.postgis_tools import update_supplier_reliability

def learn_agent_node(state: RitveerState) -> Dict[str, Any]:
    """
    The learn agent node processes feedback (delivery times, quality flags)
    and updates supplier reliability scores in the database.
    """
    print("---LEARN AGENT: Processing feedback for continuous improvement---")
    final_order = state.get("final_order", {})
    supplier_quotes = state.get("supplier_quotes", [])

    if not final_order or final_order.get("status") != "committed":
        print("LEARN AGENT: No committed order found. Skipping learning.")
        return {}

    # Assuming final_order contains information about the chosen supplier
    # and potentially delivery time/quality feedback.
    # For demonstration, let's use dummy feedback.
    
    chosen_supplier_name = final_order.get("supplier_name")
    
    if chosen_supplier_name:
        # Simulate feedback:
        # Positive feedback (e.g., on-time delivery, good quality)
        # Negative feedback (e.g., late delivery, quality issue)
        
        # For simplicity, let's assume a fixed positive score change for now
        # In a real system, this would be based on actual performance metrics
        score_change = 0.5 # Example: +0.5 for a successful delivery
        
        # You would also check for quality flags or delivery times from the state
        # For example:
        # if state.get("delivery_status") == "late":
        #     score_change -= 0.2
        # if state.get("quality_issue"):
        #     score_change -= 0.5

        print(f"LEARN AGENT: Updating reliability for {chosen_supplier_name} with change {score_change}")
        update_result = update_supplier_reliability(chosen_supplier_name, score_change)
        
        if "error" not in update_result:
            print(f"LEARN AGENT: Supplier reliability updated: {update_result}")
        else:
            print(f"LEARN AGENT: Failed to update supplier reliability: {update_result['error']}")
    else:
        print("LEARN AGENT: No chosen supplier found in final order. Skipping reliability update.")

    return {}
