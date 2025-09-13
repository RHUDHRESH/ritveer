from typing import Any, Dict, List
from src.graph.state import RitveerState
from config.settings import settings
from src.tools.razorpay_tools import create_payment_order
import uuid

def commit_agent_node(state: RitveerState) -> Dict[str, Any]:
    """
    The commit agent node applies business rules to supplier quotes,
    and if rules are met, creates a payment order and updates the state.
    """
    print("---COMMIT AGENT: Applying business rules and committing order---")
    supplier_quotes = state.get("supplier_quotes", [])
    normalized_request = state.get("normalized_request", {})

    if not supplier_quotes:
        print("COMMIT AGENT: No supplier quotes found. Cannot commit order.")
        return {"final_order": {"status": "failed", "reason": "No supplier quotes."}}

    # Get pooling rules from policy config
    pooling_rules = settings.POLICY_CONFIG.get("commit_agent", {}).get("pooling_rule", {})
    min_cost_saving_percentage = pooling_rules.get("min_cost_saving_percentage", 0.0)
    max_sla_risk_percentage = pooling_rules.get("max_sla_risk_percentage", 100.0)

    # For demonstration, let's assume the first quote is the "best"
    # In a real scenario, you'd have more sophisticated logic to select the best quote
    best_quote = supplier_quotes[0]
    
    # Simulate cost saving and SLA risk for demonstration
    # In a real scenario, these would be calculated based on actual data
    original_cost = normalized_request.get("budget", 1000.0) # Assume a budget if not provided
    quoted_price = float(best_quote.get("price", 0))
    
    cost_saving_percentage = ((original_cost - quoted_price) / original_cost) * 100 if original_cost > 0 else 0
    sla_risk_percentage = 5.0 # Dummy SLA risk

    print(f"COMMIT AGENT: Cost Saving: {cost_saving_percentage:.2f}%, SLA Risk: {sla_risk_percentage:.2f}%")

    # Check if pooling rules are met
    if (cost_saving_percentage >= min_cost_saving_percentage and
            sla_risk_percentage <= max_sla_risk_percentage):
        print("COMMIT AGENT: Pooling rules met. Creating payment order.")
        
        # Create a unique receipt ID
        receipt_id = f"order_{uuid.uuid4().hex}"
        
        # Create payment order using Razorpay tool
        payment_order = create_payment_order(
            amount=quoted_price,
            currency=best_quote.get("currency", "INR"),
            receipt=receipt_id
        )
        
        if "error" not in payment_order:
            final_order = {
                "status": "committed",
                "supplier_name": best_quote["supplier_name"],
                "item": best_quote["item"],
                "price": best_quote["price"],
                "currency": best_quote["currency"],
                "payment_order_id": payment_order.get("id"),
                "payment_link": payment_order.get("short_url"),
                "receipt_id": receipt_id
            }
            return {"final_order": final_order}
        else:
            print(f"COMMIT AGENT: Failed to create payment order: {payment_order['error']}")
            return {"final_order": {"status": "failed", "reason": "Payment order creation failed."}}
    else:
        print("COMMIT AGENT: Pooling rules not met. Cannot commit order.")
        return {"final_order": {"status": "failed", "reason": "Pooling rules not met."}}
