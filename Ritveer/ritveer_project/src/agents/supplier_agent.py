import asyncio, time, uuid
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from typing import Optional
from src.tools.messaging.telegram_client import TelegramClient
from src.tools.dao import dao, tokens
from src.tools.scoring import score_supplier_quote
import httpx
import os
from src.tools.policy import policy

class RFPMeta(BaseModel):
    rfp_id: str
    round: int
    deadline_utc: datetime
    invited_supplier_ids: list[str]

class Quote(BaseModel):
    supplier_id: str
    amount_inr: int
    lead_time_days: int
    valid_till_utc: datetime
    notes: str = ""
    incoterm: str = "DAP"
    credibility: float = 0.0
    reasons: list[str] = []
    status: str = "proposed"

class SupplierOutput(BaseModel):
    rfp: RFPMeta
    quotes: list
    shortlist: list
    fallback_quote: Optional[Quote]
    chosen_strategy: str
    risk_flags: list

async def send_rfp_telegram(client, supplier, rfp, link):
    text = f"RFP {rfp['rfp_id']} for {rfp['cluster_label']} Qty {rfp['qty']} Due {rfp['deadline_utc']:%H:%M UTC}"
    buttons = [
        [{"text": "Quote now", "url": link}],
        [{"text": "Decline", "callback_data": f"decline:{rfp['rfp_id']}"}]
    ]
    await client.send_buttons(supplier["telegram_chat_id"], text, buttons)

def score_quote(q, supplier_stats, policy):
    price_score = max(0.0, 1.0 - (q.amount_inr - policy["target_price"]) / max(1, policy["target_price"]))
    speed_score = max(0.0, 1.0 - (q.lead_time_days - policy["target_lead_time"]) / max(1, policy["target_lead_time"]))
    ot_rate = supplier_stats.get("on_time_rate", 0.8)
    qa = supplier_stats.get("qa_score", 0.8)
    proximity = supplier_stats.get("km_to_customer", 500)
    prox_score = max(0.0, 1.0 - proximity / 1000.0)
    credibility = 0.35*price_score + 0.25*speed_score + 0.2*ot_rate + 0.15*qa + 0.05*prox_score
    reasons = []
    if price_score > 0.8: reasons.append("under_band")
    if speed_score > 0.8: reasons.append("fast_lead_time")
    if ot_rate > 0.95: reasons.append("reliable")
    return credibility, reasons

async def supplier_node(state):
    print("---SUPPLIER AGENT: RFP fan-out and collection---")
    cluster = state["cluster"]["primary"]
    intake = state["intake"]
    policy = state["policy"]
    sup_prev = state.get("supplier", {})
    round_no = sup_prev.get("rfp", {}).get("round", 0) + 1
    rfp_id = sup_prev.get("rfp", {}).get("rfp_id") or str(uuid.uuid4())
    deadline = datetime.now(timezone.utc) + timedelta(minutes=policy.get("rfp_minutes", 20))

    candidates = await dao.select_suppliers(cluster, limit=policy.get("invite_cap", 6))

    client = TelegramClient()
    links = {}
    for s in candidates:
        token = tokens.sign({"rfp_id": rfp_id, "supplier_id": s["id"], "exp": int(deadline.timestamp())})
        links[s["id"]] = f"{state['settings'].get('base_url', 'http://localhost:8000')}/rfp/{token}"

    rfp = {
        "rfp_id": rfp_id,
        "cluster_label": cluster["label"],
        "qty": intake.get("entities", {}).get("quantity", 1),
        "deadline_utc": deadline
    }

    await asyncio.gather(*[
        send_rfp_telegram(client, s, rfp, links[s["id"]])
        for s in candidates
    ])

    # Wait window with polling
    poll_every = 5
    while datetime.now(timezone.utc) < deadline:
        await asyncio.sleep(poll_every)
        if await dao.enough_quotes(rfp_id, policy.get("shortlist_k", 3)):
            break

    quotes_data = await dao.fetch_quotes(rfp_id)
    quotes = [Quote(**q, valid_till_utc=datetime.now(timezone.utc)+timedelta(hours=24)) for q in quotes_data]

    shortlist = []
    pol = {"target_price": cluster["price_band_inr"][1], "target_lead_time": cluster["lead_time_days"]}
    for q in quotes:
        stats = await dao.supplier_stats(q.supplier_id)
        cred, reasons = score_quote(q.dict(), stats, pol)
        q.credibility = round(cred, 3)
        q.reasons = reasons
        # Update quote in DB with credibility and reasons
        await dao.insert_quote(q.rfp_id, q.supplier_id, q.amount_inr, q.lead_time_days, q.notes, round_no,
                               q.credibility, q.reasons)
        shortlist.append(q)
    shortlist.sort(key=lambda x: x.credibility, reverse=True)

    fallback = None
    risk_flags = []
    if not shortlist:
        hi = cluster["price_band_inr"][1]
        fallback = Quote(
            supplier_id="fallback",
            amount_inr=int(hi*1.1),
            lead_time_days=cluster["lead_time_days"]+3,
            credibility=0.5,
            reasons=["price_book", "risk_margin"],
            valid_till_utc=datetime.now(timezone.utc)+timedelta(hours=6)
        )
        risk_flags.append("no_market_quotes")

    state["supplier"] = SupplierOutput(
        rfp=RFPMeta(rfp_id=rfp_id, round=round_no, deadline_utc=deadline, invited_supplier_ids=[c["id"] for c in candidates]),
        quotes=quotes,
        shortlist=shortlist[: policy.get("shortlist_k", 3)],
        fallback_quote=fallback,
        chosen_strategy="market" if shortlist else "fallback",
        risk_flags=risk_flags
    ).dict()
    return state

def supplier_agent_node(state):  # Sync wrapper for LangGraph, now discovery
    asyncio.run(supplier_discovery_node(state))
    return state

async def supplier_discovery_node(state: dict) -> dict:
    t0 = time.time()
    prof = state.get("profile", {})
    region = prof.get("location","").split(",")[0].strip() if prof.get("location") else None
    mats = prof.get("materials") or []
    material = mats[0] if mats else "clay"
    k = policy.get().negotiation.shortlist_k

    API_BASE = os.getenv("API_BASE", "http://localhost:8000")
    async with httpx.AsyncClient(timeout=10) as c:
        try:
            r = await c.get(f"{API_BASE}/suppliers/search", params={"material": material, "region": region, "k": k})
            r.raise_for_status()
            results = r.json().get("results", [])
        except Exception:
            results = []

    state["suppliers"] = results
    out = "No suppliers found" if not results else "\n".join([f"- {s['name']} • {s['region']} • {s['band']} • rel {s['reliability']}" for s in results])
    ts = str(datetime.utcnow())
    state["events"].append({
        "ts": ts,
        "agent": "SupplierDiscoveryAgent",
        "type": "processed",
        "data": {"summary": out}
    })
    state["agents"]["SupplierDiscoveryAgent"] = {"status": "completed", "output": None, "ms": int((time.time() - t0)*1000), "reasons": []}
    return state
