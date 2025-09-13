import uuid
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from typing import Optional, Literal, List

class OpsTask(BaseModel):
    task_id: str
    reason: str
    severity: Literal["low","med","high","critical"]
    due_utc: datetime
    assigned_to: Optional[str]
    actions: List[str]
    status: Literal["open","acked","resolved","canceled"] = "open"
    resolution: Optional[str]
    notes: List[str] = []

REASONS = {
    "invalid_signature":  ("critical",  15, ["deny","reroute:Guard"]),
    "low_confidence":     ("med",       30, ["reroute:Clarify","approve"]),
    "low_coverage":       ("med",       45, ["reroute:ExpandSupply","approve"]),
    "quality_decline":    ("high",      30, ["reroute:ExpandSupply","approve"]),
    "awaiting_review":    ("high",      15, ["confirm_payment","deny"]),
    "cash_not_confirmed": ("high",      30, ["reroute:Cash","cancel"]),
    "price_outlier":      ("med",       60, ["approve","deny"]),
    "capacity_fail":      ("high",      30, ["reroute:Supplier","cancel"]),
}

def ops_reason_and_actions(state) -> tuple[str, List[str], str, datetime]:
    # pick the strongest reason in priority order
    candidates = []
    flags = []
    flags += state.get("intake",{}).get("risk_flags", [])
    flags += state.get("cluster",{}).get("primary",{}).get("risk_flags", [])
    flags += state.get("supplier",{}).get("risk_flags", [])
    if state.get("cash",{}).get("status") == "awaiting_review":
        candidates.append("awaiting_review")
    if state.get("commit",{}).get("status") == "failed" and "cash_not_confirmed" in state.get("commit",{}).get("risk_flags",[]):
        candidates.append("cash_not_confirmed")
    if state.get("learn",{}).get("anomalies", []):
        candidates.extend(state["learn"]["anomalies"])

    # map flags to reasons we care about
    for f in flags:
        if f in REASONS: candidates.append(f)

    reason = candidates[0] if candidates else "low_confidence"
    sev, minutes, actions = REASONS.get(reason, ("med", 30, ["approve","deny"]))
    due = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return reason, actions, sev, due

async def ops_node(state):
    reason, actions, severity, due = ops_reason_and_actions(state)
    task_id = state.get("ops",{}).get("task_id") or str(uuid.uuid4())
    owner = "ops_team"  # TODO: implement pick_oncall round robin

    # upsert the task
    await state["dao"].upsert_ops_task({
        "task_id": task_id, "order_id": state.get("order_id"),
        "reason": reason, "severity": severity, "due_utc": due,
        "actions": actions, "status": "open", "assigned_to": owner
    })
    state["ops"] = {
        "task_id": task_id, "reason": reason, "severity": severity,
        "due_utc": due, "actions": actions, "status": "open",
        "assigned_to": owner, "resolution": None, "notes": []
    }

    # notify ops on Telegram
    group = state.get("settings", {}).get("ops_chat_id", "ops_chat")
    msg = f"OPS {severity.upper()} for order {state.get('order_id','n/a')} - {reason}"
    btns = [[{"text":"Approve","callback_data":f"ops:{task_id}:approve"}],
            [{"text":"Deny","callback_data":f"ops:{task_id}:deny"}]]
    # add dynamic actions
    for a in actions:
        if a.startswith("reroute:"):
            target = a.split(":")[1]
            btns.append([{"text":f"Reroute {target}", "callback_data":f"ops:{task_id}:reroute:{target}"}])
        if a == "confirm_payment":
            btns.append([{"text":"Confirm payment", "callback_data":f"ops:{task_id}:confirm_cash"}])
    await state["telegram"].send_buttons(group, msg, btns)
    return state

def ops_router(state):
    task = state.get("ops", {})
    if task.get("status") in {"open","acked"}:
        return "Ops"  # loop until resolved

    # resolved with a specific resolution string
    res = task.get("resolution","")
    if res.startswith("reroute:"):
        target = res.split(":")[1]
        return target
    if res.startswith("approved"):
        # continue the original happy path based on where we came from
        if "cash_not_confirmed" in task.get("notes", []):
            return "Cash"
        if state.get("cluster"):
            return "Supplier"
        return "Learn"
    if res.startswith("denied") or res.startswith("canceled"):
        return "Clarify"
    return "Learn"
