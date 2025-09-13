from typing import Dict, Any
from twilio.rest import Client
from config.settings import settings

def parse_twilio_webhook(webhook_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Parses the incoming webhook data from Twilio to extract the sender's
    phone number and message body.

    Args:
        webhook_data: A dictionary containing the raw webhook data from Twilio.

    Returns:
        A dictionary with 'sender_phone_number' and 'message_body'.
    """
    sender_phone_number = webhook_data.get("From")
    message_body = webhook_data.get("Body")

    if not sender_phone_number or not message_body:
        raise ValueError("Missing 'From' or 'Body' in Twilio webhook data.")

    return {
        "sender_phone_number": sender_phone_number,
        "message_body": message_body,
    }

def send_sms(to_phone_number: str, message: str) -> Dict[str, Any]:
    """
    Sends an SMS message using Twilio.

    Args:
        to_phone_number: The recipient's phone number.
        message: The message body.

    Returns:
        A dictionary containing the Twilio message SID and status.
    """
    print(f"TWILIO TOOL: Sending SMS to {to_phone_number}")
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    try:
        message = client.messages.create(
            to=to_phone_number,
            from_=settings.TWILIO_PHONE_NUMBER,
            body=message
        )
        return {"sid": message.sid, "status": message.status}
    except Exception as e:
        print(f"TWILIO TOOL: Error sending SMS: {e}")
        return {"error": str(e)}

def make_call(to_phone_number: str, twiml_url: str) -> Dict[str, Any]:
    """
    Makes an automated voice call using Twilio.

    Args:
        to_phone_number: The recipient's phone number.
        twiml_url: A URL that returns TwiML instructions for the call.

    Returns:
        A dictionary containing the Twilio call SID and status.
    """
    print(f"TWILIO TOOL: Error making call: {to_phone_number}")
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    try:
        call = client.calls.create(
            to=to_phone_number,
            from_=settings.TWILIO_PHONE_NUMBER,
            url=twiml_url
        )
        return {"sid": call.sid, "status": call.status}
    except Exception as e:
        print(f"TWILIO TOOL: Error making call: {e}")
        return {"error": str(e)}