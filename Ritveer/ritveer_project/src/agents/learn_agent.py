import uuid, hashlib, json
from datetime import datetime, timezone
from pydantic import BaseModel
from src.tools.dao import dao

class LearnOutput(BaseModel):
    log_id: str
    labels: dict                  # {"won": True, "reason": "on_time", "refund": False}
    updates: dict                 # {"price_book": 1, "supplier_stats": 1, "centroid": 1}
    anomalies: list[str]          # ["price_outlier","lead_time_slip"]
    metrics: dict                 # counters and durations

def content_hash(obj: dict) -> str:
    data = json.dumps(obj, sort_keys=True, separators=(",",":")).encode()
    return hashlib.sha256(data).hexdigest()

async def learn_node(state):
    now = datetime.now(timezone.utc)
    dao = state["dao"]
    log = {"updates": {}, "anomalies": [], "labels": {}, "metrics": {}}

    # 1) final immutable snapshot
    snap = {
        "intake": state.get("intake", {}),
        "cluster": state.get("cluster", {}),
        "supplier": state.get("supplier", {}),
        "cash": state.get("cash", {}),
        "commit": state.get("commit", {}),
        "policy": state.get("policy", {}),
    }
    h = content_hash(snap)
    await dao.append_event(state["order_id"], "final_snapshot", {"hash": h})
    log["log_id"] = h

    # Extract facts
    order_id = state.get("order_id")
    cm = state.get("commit", {})
    sp = state.get("supplier", {})
    cl = state.get("cluster", {}).get("primary", {})
    qty = int(state.get("intake", {}).get("entities", {}).get("quantity", 1) or 1)
    shortlist = sp.get("shortlist", [{"supplier_id": None, "amount_inr": 0},])
    supplier_id = shortlist[0]["supplier_id"]
    price_unit = shortlist[0]["amount_inr"]
    price = price_unit * qty
    region = cl.get("location_hint", {}).get("region", "unknown")

    won = cm.get("status") in {"placed","reserved","awaiting_supplier_ack","backorder"}
    refund = False  # fill later if you implement returns
    sla_hit = None  # fill when delivered

    await dao.upsert_fact_order({
        "order_id": order_id, "cluster_id": cl.get("id"), "supplier_id": supplier_id,
        "qty": qty, "price_inr": price_unit, "lead_time_days": cl.get("lead_time_days", 7),
        "region": region, "won": won, "refund": refund, "sla_hit": sla_hit, "amount_inr": price
    })

    # 2) price book
    band = await dao.update_price_book(cl.get("id"), price_unit)
    log["updates"]["price_book"] = 1
    # flag outlier
    if price_unit > band["p90_inr"] * state["policy"].get("price_outlier_multiplier", 1.15):
        log["anomalies"].append("price_outlier")

    # 3) supplier stats
    if supplier_id:
        await dao.update_supplier_stats(supplier_id, cl.get("id"), cl.get("lead_time_days", 7), won)
        log["updates"]["supplier_stats"] = 1

    # 4) coverage index
    await dao.recompute_coverage(cl.get("id"), region)
    log["updates"]["coverage"] = 1

    # 5) centroid update
    if "centroid" in cl and cl["centroid"]:
        await dao.update_cluster_centroid(cl.get("id"), cl["centroid"])
        log["updates"]["centroid"] = 1

    # 6) labels
    log["labels"] = {"won": won, "refund": refund, "sla_hit": sla_hit}

    state["learn"] = {
        "log_id": log["log_id"],
        "labels": log["labels"],
        "updates": log["updates"],
        "anomalies": log["anomalies"],
        "metrics": log["metrics"]
    }
    return state
