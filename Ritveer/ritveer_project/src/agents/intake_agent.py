import time
import hashlib
import os
import redis
from typing import Optional, Literal, Dict, List, Any
from pydantic import ValidationError

from ritveer_project.src.graph.state import IntakeOutput

# Initialize Redis client
# In a real application, this would be configured more robustly,
# e.g., using a connection pool or dependency injection.
try:
    r = redis.Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
except Exception as e:
    print(f"Could not connect to Redis: {e}. Proceeding without Redis for now.")
    r = None # Set r to None if connection fails

def make_request_id(msg_sid: str, body: str) -> str:
    """Generates a unique request ID for idempotency."""
    digest = hashlib.sha256(body.encode('utf-8')).hexdigest()[:16]
    return f"{msg_sid}-{digest}"

def run_intake_pipeline(raw_message: str, channel: Literal["whatsapp", "web", "ops_console"], msg_sid: Optional[str] = None, twilio_signature: Optional[str] = None, request_url: Optional[str] = None) -> IntakeOutput:
    """
    Processes an inbound message through the Intake pipeline.

    Args:
        raw_message: The raw text content of the inbound message.
        channel: The channel from which the message originated.
        msg_sid: The Message SID from Twilio, if applicable.
        twilio_signature: The X-Twilio-Signature header, if applicable.
        request_url: The full URL of the incoming webhook request, if applicable.

    Returns:
        An IntakeOutput Pydantic model instance.
    """
    start_time = time.perf_counter()
    timings_ms: Dict[str, int] = {}
    risk_flags: List[str] = []
    meta: Dict[str, str] = {}

    # --- 1. Idempotency and de-dupe ---
    # This step is partially handled in the webhook, but we can add a check here too
    # and update meta if it's a known duplicate.
    request_id = "req_unknown"
    if msg_sid:
        request_id = make_request_id(msg_sid, raw_message)
        if r and not r.setnx(f"intake:seen:{request_id}", 1):
            meta["duplicate"] = "true"
            # If it's a duplicate, we might want to short-circuit or return a minimal IntakeOutput
            # For now, we'll let it proceed but mark it.
        if r:
            r.expire(f"intake:seen:{request_id}", 120) # Expire after 2 minutes

    timings_ms["dedupe"] = int((time.perf_counter() - start_time) * 1000)

    # --- 2. Security gate (Twilio signature verification) ---
    # This is primarily handled in the webhook, but risk_flags can be set here
    # if the webhook passes a flag indicating invalid signature.
    # For this function, we assume the webhook has already done the primary check.
    # If the webhook explicitly passed an invalid signature, we'd add it to risk_flags.
    # Example: if not is_twilio_signature_valid(twilio_signature, request_url, raw_message):
    #     risk_flags.append("invalid_signature")
    # For now, we'll assume valid if twilio_signature is provided and not explicitly marked invalid.
    # If the webhook already set "invalid_signature", it would be passed in via a state object,
    # which is not directly available here. This function assumes a "clean" raw_message.
    # The webhook will set the risk_flags in the state directly if signature is invalid.

    timings_ms["security_gate"] = int((time.perf_counter() - start_time) * 1000) - timings_ms.get("dedupe", 0)

    # --- 3. Lightweight language and spam checks ---
    language = "en" # Default
    # Example:
    # from langdetect import detect
    # try:
    #     language = detect(raw_message)
    # except:
    #     pass # Fallback to default
    # if is_spam_heuristic(raw_message):
    #     risk_flags.append("spam")
    # if contains_profanity(raw_message):
    #     risk_flags.append("profane")

    timings_ms["lang_spam_check"] = int((time.perf_counter() - start_time) * 1000) - sum(timings_ms.values())

    # --- 4. Normalization ---
    normalized_text = raw_message.strip()
    # Example:
    # normalized_text = normalize_whitespace(normalized_text)
    # normalized_text = normalize_numbers(normalized_text)
    # ... phone, address normalization helpers

    timings_ms["normalization"] = int((time.perf_counter() - start_time) * 1000) - sum(timings_ms.values())

    # --- 5. Intent classification tiered ---
    intent = "unsupported"
    intent_confidence = 0.0
    priority: Literal["low", "normal", "high", "urgent"] = "normal"

    # Tier 1: Rules and keyword lattices
    # if "urgent order" in normalized_text.lower():
    #     intent = "place_order"
    #     intent_confidence = 0.95
    #     priority = "urgent"
    # elif "payment issue" in normalized_text.lower():
    #     intent = "payment_inquiry"
    #     intent_confidence = 0.9
    #     priority = "high"
    # else:
    # Tier 2: Ollama local model (placeholder)
    #     ollama_response = call_ollama_for_intent(normalized_text)
    #     intent = ollama_response.intent
    #     intent_confidence = ollama_response.confidence
    #     if intent_confidence < 0.6:
    #         # Tier 3: Fallback to reasoning model (placeholder)
    #         reasoning_model_response = call_reasoning_model(normalized_text)
    #         intent = reasoning_model_response.intent
    #         intent_confidence = reasoning_model_response.confidence
    #         meta["model_tier"] = "reasoning"
    #     else:
    #         meta["model_tier"] = "ollama"

    # Dummy intent for now
    if "order" in normalized_text.lower():
        intent = "place_order"
        intent_confidence = 0.8
        priority = "normal"
    elif "help" in normalized_text.lower():
        intent = "support_request"
        intent_confidence = 0.7
        priority = "low"
    else:
        intent = "general_inquiry"
        intent_confidence = 0.5
        priority = "normal"

    timings_ms["intent_classification"] = int((time.perf_counter() - start_time) * 1000) - sum(timings_ms.values())

    # --- 6. Entity extraction and slot analysis ---
    entities: Dict[str, str] = {}
    slot_gaps: List[str] = []
    # Example:
    # if intent == "place_order":
    #     if "quantity" not in normalized_text.lower():
    #         slot_gaps.append("quantity")
    #     if "item" not in normalized_text.lower():
    #         slot_gaps.append("item")
    #     entities["item"] = extract_item(normalized_text)
    #     entities["quantity"] = extract_quantity(normalized_text)

    timings_ms["entity_slot_analysis"] = int((time.perf_counter() - start_time) * 1000) - sum(timings_ms.values())

    # --- 7. Policy and guardrails ---
    # Example:
    # if is_blacklisted_word(normalized_text):
    #     risk_flags.append("blacklist_hit")
    # if is_supplier_blocked(entities.get("supplier_id")):
    #     risk_flags.append("supplier_blocked")
    # if check_velocity_limit(customer_id, channel):
    #     risk_flags.append("velocity_limit_exceeded")

    timings_ms["policy_guardrails"] = int((time.perf_counter() - start_time) * 1000) - sum(timings_ms.values())

    # --- 8. Next hop hint ---
    next_actions_hint: Optional[str] = None
    if "spam" in risk_flags or "invalid_signature" in risk_flags or "blacklist_hit" in risk_flags:
        next_actions_hint = "guard_agent"
    elif meta.get("duplicate") == "true":
        next_actions_hint = "drop" # Handled by router, but good to hint
    elif intent == "unsupported":
        next_actions_hint = "ops_agent"
    elif slot_gaps:
        next_actions_hint = "clarify_agent"
    elif language not in {"en", "hi"}: # Assuming "en", "hi" are supported directly
        next_actions_hint = "translate_agent"
    else:
        next_actions_hint = "cluster_agent"

    timings_ms["next_hop_hint"] = int((time.perf_counter() - start_time) * 1000) - sum(timings_ms.values())

    # Construct the IntakeOutput
    try:
        output = IntakeOutput(
            request_id=request_id,
            conversation_id="conv_" + request_id, # Dummy for now
            customer_id="cust_unknown", # Dummy for now
            channel=channel,
            raw_text=raw_message,
            language=language,
            translated_text=None, # Placeholder
            intent=intent,
            intent_confidence=intent_confidence,
            priority=priority,
            entities=entities,
            slot_gaps=slot_gaps,
            risk_flags=risk_flags,
            next_actions_hint=next_actions_hint,
            meta=meta,
            timings_ms=timings_ms
        )
    except ValidationError as e:
        print(f"IntakeOutput validation error: {e}")
        # Fallback to a minimal valid output or raise an error
        output = IntakeOutput(
            request_id=request_id,
            conversation_id="conv_error",
            channel=channel,
            raw_text=raw_message,
            language="en",
            intent="error",
            intent_confidence=0.0,
            risk_flags=["validation_error"],
            next_actions_hint="ops_agent"
        )

    return output