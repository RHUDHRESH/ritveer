import os, uuid
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from typing import Literal
from src.tools.dao import dao
from src.tools.messaging.telegram_client import TelegramClient
from src.tools.pdf.po import purchase_order

class CommitEvent(BaseModel):
    ts_utc: datetime
    type: Literal["validated","po_created","po_sent","reserve_ok","reserve_failed","ship_task","customer_notified","rollback"]
    data: dict = {}

class CommitState(BaseModel):
    order_id: str
    po_id: str
    supplier_id: str
    amount_inr: int
    qty: int
    lead_time_days: int
    eta_utc: datetime
    status: Literal["placed","awaiting_supplier_ack","reserved","backorder","failed"] = "placed"
    artifacts: dict                     # {"po_pdf_path": "...", "po_number":"..."}
    events: list[CommitEvent]
    risk_flags: list[str]

def must_prepay(policy, state) -> bool:
    if not policy.get("prepay_required"):
        return False
    # new customer or high amount forces prepay
    amount = state["supplier"]["shortlist"][0]["amount_inr"] * int(state["intake"]["entities"].get("quantity",1))
    return state.get("customer",{}).get("is_new", True) or amount >= policy.get("prepay_threshold_inr", 3000)

def po_number(now: datetime, order_id: str) -> str:
    return f"PO-{now:%Y%m%d}-{order_id[:8].upper()}"

async def commit_node(state):
    policy = state["policy"]
    now = datetime.now(timezone.utc)
    events = []

    # Preconditions
    quote = state["supplier"]["shortlist"][0]
    qty = int(state["intake"]["entities"].get("quantity", 1))
    amount = quote["amount_inr"] * qty

    if must_prepay(policy, state) and state.get("cash",{}).get("status") != "confirmed":
        # hard stop and route back to Cash or Ops
        state["commit"] = {
            "order_id": state.get("order_id") or str(uuid.uuid4()),
            "po_id": "",
            "supplier_id": quote["supplier_id"],
            "amount_inr": amount,
            "qty": qty,
            "lead_time_days": quote["lead_time_days"],
            "eta_utc": now + timedelta(days=quote["lead_time_days"]),
            "status": "failed",
            "artifacts": {},
            "events": [{"ts_utc": now, "type": "validated", "data": {"reason":"cash_not_confirmed"}}],
            "risk_flags": ["cash_not_confirmed"]
        }
        return state

    # Idempotency by order_id
    order_id = state.get("order_id")
    if not order_id:
        order_id = str(uuid.uuid4())
        state["order_id"] = order_id
    cm = state.get("commit")

    existing = await dao.get_order_by_id(order_id)
    if existing:
        state["commit"] = existing["commit_snapshot"]
        return state

    # Create order + PO in DB
    po_id = str(uuid.uuid4())
    eta = now + timedelta(days=quote["lead_time_days"])
    po_num = po_number(now, order_id)
    await dao.create_order({
        "order_id": order_id,
        "customer_id": state.get("customer",{}).get("id"),
        "supplier_id": quote["supplier_id"],
        "cluster_id": state["cluster"]["primary"]["id"],
        "qty": qty, "amount_inr": amount, "po_id": po_id, "po_number": po_num,
        "eta_utc": eta, "status": "placed", "cash_id": state.get("cash",{}).get("payment_id")
    })

    # Generate PO PDF
    client = TelegramClient()
    pdf_path = await purchase_order({
        "po_number": po_num,
        "order_id": order_id,
        "supplier_name": await dao.supplier_name(quote["supplier_id"]),
        "lines": [{"label": state["cluster"]["primary"]["label"], "qty": qty, "price_inr": quote["amount_inr"]}],
        "total_inr": amount,
        "ship_to": state["intake"]["entities"].get("address",""),
        "terms": "UPI paid" if state.get("cash",{}).get("status") == "confirmed" else "COD"
    })

    events.append({"ts_utc": now, "type": "po_created", "data": {"po_number": po_num, "pdf": pdf_path}})

    # Send PO to supplier over Telegram with an Ack button
    supplier_chat = await dao.supplier_chat_id(quote["supplier_id"])
    await client.send_text(supplier_chat, f"New PO {po_num} for Order {order_id}. Total INR {amount}.")
    await client.send_buttons(supplier_chat, "Please acknowledge or decline.",
        [[{"text":"Acknowledge", "callback_data": f"po_ack:{po_id}"},
          {"text":"Decline", "callback_data": f"po_decline:{po_id}"}]])
    events.append({"ts_utc": now, "type":"po_sent", "data":{"supplier_chat": supplier_chat}})

    # Soft reservation hook
    reserved = await dao.reserve_capacity(quote["supplier_id"], state["cluster"]["primary"]["id"], qty)
    events.append({"ts_utc": now, "type":"reserve_ok" if reserved else "reserve_failed", "data": {"qty": qty}})
    status = "reserved" if reserved else "awaiting_supplier_ack"

    # Create shipping task placeholder for manual CSV later
    await dao.create_ship_task({"order_id": order_id, "status":"pending", "mode":"manual_csv"})
    events.append({"ts_utc": now, "type":"ship_task", "data":{"mode":"manual_csv"}})

    state["commit"] = {
        "order_id": order_id,
        "po_id": po_id,
        "supplier_id": quote["supplier_id"],
        "amount_inr": amount,
        "qty": qty,
        "lead_time_days": quote["lead_time_days"],
        "eta_utc": eta,
        "status": status,
        "artifacts": {"po_pdf_path": pdf_path, "po_number": po_num},
        "events": events,
        "risk_flags": [] if reserved else ["no_capacity_reservation"]
    }
    return state
