import razorpay
from typing import Dict, Any
from config.settings import settings
import requests # Import requests to catch connection errors
from src.utils.redis_utils import add_to_retry_stream

def create_payment_order(amount: float, currency: str, receipt: str) -> Dict[str, Any]:
    """
    Creates a payment order using the Razorpay API.

    Args:
        amount: The amount to be paid (in the smallest currency unit, e.g., paise for INR).
        currency: The currency of the payment (e.g., "INR").
        receipt: A unique identifier for the order.

    Returns:
        A dictionary containing the Razorpay order details, or an error message.
    """
    print(f"RAZORPAY TOOL: Creating payment order for {amount} {currency}")
    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        # Razorpay amount is in the smallest unit (e.g., paise for INR)
        # Convert amount to integer paise
        amount_paise = int(amount * 100)

        order_payload = {
            "amount": amount_paise,
            "currency": currency,
            "receipt": receipt,
            "payment_capture": '1'  # Auto capture payment
        }
        
        order = client.order.create(order_payload)
        return order
    except requests.exceptions.ConnectionError as e:
        print(f"RAZORPAY TOOL: Network error creating payment order: {e}. Queuing for retry.")
        task_details = {
            "agent": "commit_agent", # Assuming commit_agent calls this tool
            "tool": "create_payment_order",
            "args": {"amount": amount, "currency": currency, "receipt": receipt}
        }
        add_to_retry_stream(task_details)
        return {"status": "retry_queued", "message": f"Network error: {str(e)}. Task queued for retry."}
    except Exception as e:
        print(f"RAZORPAY TOOL: Error creating payment order: {e}")
        return {"status": "failed", "message": f"Razorpay API error: {str(e)}"}
