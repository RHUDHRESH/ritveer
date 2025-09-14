from langgraph.graph import StateGraph, END
from typing import Dict, Any
from pydantic import BaseModel
from datetime import datetime
from src.tools.policy import policy as policy_store

# Initialize state with contract
def initialize_state(**kwargs) -> Dict[str, Any]:
    state = {
        "messages": [],
        "profile": {},
        "story": {},
        "bom": {},
        "suppliers": [],
        "quote": {},
        "events": [],
        "artifacts": {},
        "policy": policy_store.dict(),
        "agents": {},
    }
    state.update(kwargs)
    return state

class RitveerState(Dict[str, Any]):
    pass  # Define as needed based on your state structure

# Import all agent node functions
from src.agents.intake_agent import run_intake_pipeline
from src.agents.guard_agent import guard_node
from src.agents.cluster_agent import cluster_agent_node
from src.agents.clarify_agent import clarify_node
from src.agents.supplier_agent import supplier_agent_node
from src.agents.commit_agent import commit_node
from src.agents.ops_agent import ops_node, ops_router
from src.agents.cash_agent import cash_agent_node
from src.agents.learn_agent import learn_node
from src.agents.sales_agent import sales_agent_node
from src.agents.translate_agent import translate_agent_node


# Initialize the StateGraph with our RitveerState schema
workflow = StateGraph(RitveerState)

# Note: LLM clients should be instantiated at runtime with proper environment variables
# fast_llm = ChatOllama(model="gemma3:1b", base_url=settings.OLLAMA_HOST)
# reasoning_llm = ChatOllama(model="gemma3:4b", base_url=settings.OLLAMA_HOST)

# --- Intake Node and Router ---
def intake_node(state: RitveerState) -> RitveerState:
    print("Executing Intake Node...")
    # Assuming raw_message and channel are passed in the initial state
    # from the webhook.
    raw_message = state.get("raw_message", "")
    channel = state.get("channel", "whatsapp")
    
    # Pass any other relevant info from state to run_intake_pipeline
    # For now, we'll assume the webhook populates raw_message and channel
    # and the intake pipeline handles the rest.
    
    intake_output = run_intake_pipeline(raw_message=raw_message, channel=channel)
    state["intake"] = intake_output.model_dump()
    return state

def intake_router(state: RitveerState) -> str:
    print("Executing Intake Router...")
    intake_output = state.get("agents", {}).get("intake", {}).get("output")
    if not intake_output:
        return "Ops" # Fallback if intake data is missing

    flags = set(intake_output.get("risk_flags", []))
    if "invalid_signature" in flags or "spam" in flags or "blacklist_hit" in flags:
        print("---ROUTER: Routing to Guard Agent (Risk Flags)---")
        return "Guard"
    if intake_output.get("meta", {}).get("duplicate") == "true":
        print("---ROUTER: Routing to END (Duplicate)---")
        return "drop"
    if intake_output.get("intent") == "unsupported":
        print("---ROUTER: Routing to Ops Agent (Unsupported Intent)---")
        return "Ops"
    if intake_output.get("slot_gaps"):
        print("---ROUTER: Routing to Clarify Agent (Slot Gaps)---")
        return "Clarify"
    if intake_output.get("language") not in {"en","hi"}: # Assuming "en", "hi" are supported directly
        print("---ROUTER: Routing to Translate Agent (Unsupported Language)---")
        return "Translate"

    print("---ROUTER: Routing to Cluster Agent (Happy Path)---")
    return "Cluster"

# Add Nodes to Graph
workflow.add_node("Intake", intake_node)
workflow.add_node("Guard", guard_node)
workflow.add_node("Ops", ops_node)
workflow.add_node("Clarify", clarify_node)
workflow.add_node("Translate", translate_agent_node)
workflow.add_node("Cluster", cluster_agent_node)
workflow.add_node("Supplier", supplier_agent_node)
workflow.add_node("Commit", commit_node)
workflow.add_node("Cash", cash_agent_node)
workflow.add_node("Learn", learn_node)
workflow.add_node("Sales", sales_agent_node)


# Define Conditional Edge for Sales Agent
def route_to_sales(state: RitveerState) -> str:
    """
    Determines whether to route to the SalesAgent based on the presence of a sales_task.
    """
    # This logic might need to be updated to use intake.entities or intake.intent
    # For now, keeping it as is, assuming normalized_request might still be used
    # or will be derived from intake.
    normalized_request = state.get("normalized_request", {})
    if normalized_request.get("sales_task"):
        print("---ROUTER: Routing to SalesAgent---")
        return "Sales"
    else:
        print("---ROUTER: Routing to CashAgent---")
        return "Cash"

# Define Conditional Edge for Cluster Agent
def route_after_cluster(state: RitveerState) -> str:
    """
    Determines whether to route to the SupplierAgent or CommitAgent based on clustered suppliers.
    """
    clustered_suppliers = state.get("clustered_suppliers", [])
    if not clustered_suppliers:
        print("---ROUTER: No clustered suppliers found. Routing to CommitAgent.---")
        return "Commit"
    else:
        print("---ROUTER: Clustered suppliers found. Routing to SupplierAgent.---")
        return "Supplier"

# Define Edges
workflow.set_entry_point("Intake")
workflow.add_conditional_edges(
    "Intake",
    intake_router,
    {
        "Guard": "Guard",
        "drop": END,
        "Ops": "Ops",
        "Clarify": "Clarify",
        "Translate": "Translate",
        "Cluster": "Cluster"
    },
)

def guard_router(state: RitveerState) -> str:
    g = state.get("guard", {})
    if g.get("action") == "pass":
        return "Cluster"
    if g.get("action") == "clarify":
        return "Clarify"
    if g.get("action") == "ops":
        return "Ops"
    return "__end__"  # drop

def clarify_router(state):
    cl = state.get("clarify", {})
    if cl.get("pending_slots"):
        if state.get("now_utc") and cl.get("deadline_utc") and state["now_utc"] > cl["deadline_utc"] and cl.get("failures", 0) >= 2:
            return "Ops"
        return "Clarify"  # keep the loop until done or timeout
    # done: pick destination
    hint = cl.get("next_hint")
    if hint == "cluster":
        return "Cluster"
    if hint == "cash":
        return "Cash"
    return "Cluster"

workflow.add_conditional_edge("Guard", guard_router, {
    "Cluster": "Cluster",
    "Clarify": "Clarify",
    "Ops": "Ops",
    "__end__": END
})
workflow.add_conditional_edge("Clarify", clarify_router, {
    "Clarify": "Clarify",
    "Cluster": "Cluster",
    "Cash": "Cash",
    "Ops": "Ops"
})
workflow.add_edge("Translate", "Intake") # After translation, loop back to Intake for re-processing

workflow.add_conditional_edge("Cluster", route_after_cluster)
def supplier_router(state: RitveerState) -> str:
    sup = state.get("supplier", {})
    if sup.get("shortlist"):
        best = sup["shortlist"][0]
        if best.get("credibility", 0) >= state.get("policy", {}).get("min_quote_cred", 0.5):
            return "Cash" if state.get("policy", {}).get("prepay_required", False) else "Commit"
        return "Ops"
    if sup.get("rfp", {}).get("round", 0) < 2 and state.get("coverage", {}).get("has_candidates", False):
        return "Supplier"  # second round
    return "Ops" if sup.get("fallback_quote") else "Ops"  # fallback or ops

# Replace static edge with conditional
workflow.add_conditional_edge("Supplier", supplier_router)

def commit_router(state: RitveerState) -> str:
    cm = state.get("commit", {})
    if cm.get("status") in {"placed", "reserved", "awaiting_supplier_ack", "backorder"}:
        return "Learn"  # record outcomes and move on
    if cm.get("status") == "failed":
        return "Ops"    # human fix
    return "Commit"     # loop while finishing tasks

workflow.add_conditional_edge("Commit", commit_router, {"Learn": "Learn", "Ops": "Ops", "Commit": "Commit"})

workflow.add_conditional_edge("Ops", ops_router, {
    "Ops": "Ops",
    "Clarify": "Clarify",
    "Cash": "Cash",
    "Supplier": "Supplier",
    "Learn": "Learn"
})
workflow.add_edge("Sales", "Cash")

# Define Conditional Edge for Cash Agent
def route_after_cash(state: RitveerState) -> str:
    """
    Determines whether to route to manual review or continue based on cash risk.
    """
    if state.get("cash_risk_high"):
        print("---ROUTER: High cash risk detected. Routing to END for manual review.---")
        return END # Or a dedicated manual review agent
    else:
        print("---ROUTER: No high cash risk. Routing to LearnAgent.---")
        return "Learn"

workflow.add_conditional_edge("Cash", route_after_cash)

# Set End Points
workflow.add_edge("Learn", END)

# Compile the Graph
compiled_workflow = workflow.compile()

def create_app():
    """Factory function to create and return the compiled workflow"""
    return compiled_workflow

# Export the compiled workflow
app = create_app()
