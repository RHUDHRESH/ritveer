import os, re, time
from typing import Dict, Any, List
from pydantic import BaseModel

JAILBREAK = re.compile(r"(ignore\s+previous|bypass|system\s*prompt|do\s+anything|developer\s+mode)", re.I)
PROFANITY = re.compile(r"\b(fuck|shit|bitch|bastard)\b", re.I)
URL = re.compile(r"https?://\S+", re.I)
ZERO_WIDTH = re.compile(r"[\u200B-\u200D\uFEFF]")

def sanitize(text: str, policy) -> str:
    """Clean text for downstream safety"""
    # Remove zero-width characters
    t = ZERO_WIDTH.sub("", text)
    # Collapse multiple whitespace
    t = re.sub(r"\s+", " ", t).strip()
    # Normalize quotes
    t = t.replace('"', '"').replace('"', '"')
    # Handle links per policy
    if not policy.get("allow_links", True):
        t = URL.sub("[link removed]", t)
    return t

def has_blacklist(text: str, words: List[str]) -> bool:
    """Check for blacklisted content"""
    for w in words:
        if w and re.search(rf"\b{re.escape(w)}\b", text, re.I):
            return True
    return False

class GuardResult(BaseModel):
    action: str = "pass"  # pass, clarify, ops, drop
    reasons: List[str] = []
    sanitized_text: str = ""
    ttl_seconds: int = 0

async def guard_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Guard agent: Security gatekeeper for preventing abuse and protecting downstream costs"""

    # Extract inputs
    intake = state.get("intake", {})
    text = intake.get("raw_text", "") or ""
    req_id = intake.get("request_id")
    risk_flags = intake.get("risk_flags", [])
    chat_id = str(intake.get("meta", {}).get("chat_id", "anon"))

    policy = state.get("policy", {}).get("guard", {})
    redis = state.get("redis")

    reasons = []
    action = "pass"
    ttl = 0

    # 1) Invalid signature - hard drop unless override
    if "invalid_signature" in risk_flags and policy.get("drop_on_invalid_signature", True):
        reasons.append("invalid_signature")
        action = "drop"

    # 2) Replay protection - dedupe requests
    if req_id and redis and action != "drop":
        key = f"guard:seen:{req_id}"
        if not redis.setnx(key, 1):
            reasons.append("replay")
            action = "drop"
        else:
            ttl_sec = policy.get("dedupe_ttl_s", 120)
            redis.expire(key, ttl_sec)

    # 3) Rate limiting per user
    if chat_id != "anon" and redis and action != "drop":
        burst_n = policy.get("per_user_burst_n", 5)
        window_s = policy.get("per_user_burst_window_s", 30)

        # Use sliding window by rounding timestamp
        window_key = f"guard:rate:{chat_id}:{int(time.time() // window_s)}"
        count = redis.incr(window_key, 1)

        if count == 1:
            redis.expire(window_key, window_s)

        if count > burst_n:
            reasons.append("high_velocity")
            action = "clarify"
            ttl = window_s

    # 4) Blacklisted content - route to ops for review
    blacklist_words = policy.get("blacklist_words", [])
    if has_blacklist(text, blacklist_words) and action != "drop":
        reasons.append("blacklist_hit")
        action = "ops"

    # 5) Profanity check
    if PROFANITY.search(text) and not policy.get("allow_profanity", False) and action == "pass":
        reasons.append("profanity")
        action = "clarify"

    # 6) Prompt injection detection
    if JAILBREAK.search(text) and action == "pass":
        reasons.append("prompt_injection")
        action = "clarify"

    # Sanitize text for downstream use
    sanitized = sanitize(text, policy)

    # Store result
    state["guard"] = GuardResult(
        action=action,
        reasons=reasons,
        sanitized_text=sanitized,
        ttl_seconds=ttl
    )

    # If passing, replace raw_text with sanitized version
    if action == "pass":
        intake["raw_text"] = sanitized

    return state
