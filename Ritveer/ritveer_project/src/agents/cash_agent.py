from typing import Any, Dict
from src.graph.state import RitveerState
from config.settings import settings
from src.tools.postgis_tools import record_transaction

def cash_agent_node(state: RitveerState) -> Dict[str, Any]:
    """
    The cash agent node records payment transactions in the ledger
    and checks against financial policy rules.
    """
    print("---CASH AGENT: Processing financial reconciliation---")
    final_order = state.get("final_order", {})

    if not final_order or final_order.get("status") != "committed":
        print("CASH AGENT: No committed order found. Skipping cash agent.")
        return {}

    payment_order_id = final_order.get("payment_order_id")
    amount = float(final_order.get("price", 0))
    currency = final_order.get("currency", "INR")
    order_id = final_order.get("receipt_id")

    if not payment_order_id or not amount:
        print("CASH AGENT: Missing payment details. Skipping transaction recording.")
        return {}

    # Get ledger quarantine rules from policy config
    ledger_rules = settings.POLICY_CONFIG.get("cash_agent", {}).get("ledger_quarantine", {})
    max_unapproved_delta_inr = ledger_rules.get("max_unapproved_delta_inr", 0)

    transaction_status = "approved"
    if amount > max_unapproved_delta_inr:
        transaction_status = "pending_approval"
        print(f"CASH AGENT: Transaction amount {amount} exceeds "
              f"max_unapproved_delta_inr {max_unapproved_delta_inr}. "
              "Setting status to 'pending_approval'.")

    # Record the transaction in the ledger
    transaction_record = record_transaction(
        transaction_id=payment_order_id,
        order_id=order_id,
        amount=amount,
        currency=currency,
        transaction_type="payment_in", # Assuming this is an incoming payment
        status=transaction_status
    )

    if "error" not in transaction_record:
        print(f"CASH AGENT: Transaction recorded successfully with status: {transaction_status}")
        if transaction_status == "pending_approval":
            return {"cash_risk_high": True, "cash_agent_outcome": "pending_manual_review"}
        else:
            return {"cash_risk_high": False, "cash_agent_outcome": "approved"}
    else:
        print(f"CASH AGENT: Failed to record transaction: {transaction_record['error']}")
        return {"error": "Failed to record transaction.", "cash_agent_outcome": "failed"}
