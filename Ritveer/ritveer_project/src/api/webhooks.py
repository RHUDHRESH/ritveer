from fastapi import APIRouter, Request, HTTPException, Depends, Form
from twilio.request_validator import RequestValidator
import hmac, hashlib, base64, os, redis
from typing import Dict, Optional

from ritveer_project.src.graph.state import RitveerState

# Initialize Redis client
# In a real application, this would be configured more robustly,
# e.g., using a connection pool or dependency injection.
try:
    r = redis.Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
except Exception as e:
    print(f"Could not connect to Redis: {e}. Proceeding without Redis for now.")
    r = None # Set r to None if connection fails

router = APIRouter()

def make_request_id(msg_sid: str, body: str) -> str:
    """
    Generates a unique request ID from Twilio MessageSid and HMAC of the body.
    """
    digest = hashlib.sha256(body.encode('utf-8')).hexdigest()[:16]
    return f"{msg_sid}-{digest}"

@router.post("/hooks/whatsapp")
async def whatsapp_hook(request: Request, 
                        MessageSid: Optional[str] = Form(None),
                        Body: Optional[str] = Form(None),
                        **kwargs):
    
    raw_body = await request.body()
    url = str(request.url)
    signature = request.headers.get("X-Twilio-Signature", "")
    twilio_auth_token = os.environ.get("TWILIO_AUTH_TOKEN")

    if not twilio_auth_token:
        print("TWILIO_AUTH_TOKEN not set. Skipping signature validation.")
        valid_signature = False # Treat as invalid if token is missing
    else:
        validator = RequestValidator(twilio_auth_token)
        # Twilio validator expects a dict of form parameters
        form_params = {k: v for k, v in request._form.items()} if request._form else {}
        valid_signature = validator.validate(url, form_params, signature)

    msg_sid = MessageSid or "unknown"
    request_id = make_request_id(msg_sid, Body or "")

    # --- De-dupe and Rate Limit ---
    if r:
        if not r.setnx(f"intake:seen:{request_id}", 1):
            print(f"Duplicate request detected: {request_id}")
            return {"status": "duplicate", "request_id": request_id}
        r.expire(f"intake:seen:{request_id}", 120) # Expire after 2 minutes
    else:
        print("Redis not connected. Skipping de-duplication.")

    # Prepare initial state for the graph
    initial_state: RitveerState = {
        "raw_message": Body or "",
        "channel": "whatsapp",
        "intake": {
            "request_id": request_id,
            "conversation_id": "conv_" + request_id, # Placeholder
            "raw_text": Body or "",
            "channel": "whatsapp",
            "language": "en", # Will be detected by intake_agent
            "intent": "unknown", # Will be classified by intake_agent
            "intent_confidence": 0.0,
            "priority": "normal",
            "entities": {},
            "slot_gaps": [],
            "risk_flags": [],
            "meta": {},
            "timings_ms": {},
        }
    }

    if not valid_signature:
        print(f"Invalid Twilio signature for request: {request_id}")
        initial_state["intake"]["risk_flags"].append("invalid_signature")
        initial_state["intake"]["next_actions_hint"] = "guard_agent" # Hint for router

    # Kick the graph
    # The graph expects a dictionary, not a Pydantic model for initial state
    # The intake_node will then populate the 'intake' key with IntakeOutput
    result = await request.app.state.workflow.ainvoke(initial_state)
    
    # Extract next_actions_hint from the final state of the intake agent
    final_intake_output = result.get("intake")
    next_action = final_intake_output.get("next_actions_hint") if final_intake_output else "unknown"

    return {"status": "ok", "request_id": request_id, "next": next_action}
