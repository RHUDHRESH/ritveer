from typing import Dict, List, Optional, TypedDict, Literal, Any
from pydantic import BaseModel, Field, constr
from langchain_core.messages import BaseMessage


class IntakeOutput(BaseModel):
    request_id: constr(strip_whitespace=True, min_length=8)
    conversation_id: str
    customer_id: Optional[str]
    channel: Literal["whatsapp","web","ops_console"]
    raw_text: str
    language: str
    translated_text: Optional[str]
    intent: str
    intent_confidence: float = Field(ge=0.0, le=1.0)
    priority: Literal["low","normal","high","urgent"] = "normal"
    entities: Dict[str, str] = {}
    slot_gaps: List[str] = []
    risk_flags: List[str] = []
    next_actions_hint: Optional[str]
    meta: Dict[str, str] = {}            # model, rule versions
    timings_ms: Dict[str, int] = {}      # per substep

class ClusterCandidate(BaseModel):
    id: str
    label: str
    confidence: float
    reasons: List[str]
    centroid: List[float]            # optional for audit
    price_band_inr: tuple[int, int]  # min,max
    lead_time_days: int
    location_hint: dict              # {"lat":..., "lon":..., "radius_km":...}
    risk_flags: List[str]            # e.g. ["low_coverage","quality_decline"]

class ClusterOutput(BaseModel):
    primary: Optional[ClusterCandidate]
    alternates: List[ClusterCandidate] = []
    disambiguation_keys: List[str] = []   # which missing slots matter most
    chosen_strategy: Literal["exact","nearest","fallback","rules_only", "skipped"]
    metrics: Dict[str, float] = {}        # latency, neighbors_scanned, etc


class RitveerState(TypedDict, total=False):
    """
    Represents the state of our graph. It contains the following:

    - `initial_query`: The initial query from the user, which is often a question or task.
    - `chat_history`: A list of all messages in the current conversation.
    - `current_agent_name`: The name of the agent currently responsible for responding.
    - `tool_code`: Any code that the current agent wants to execute.
    - `tool_output`: The output of any tool code that was executed.
    - `parsed_tool_output`: The parsed output of any tool code that was executed.
    - `error`: Any error message that occurred during the execution.
    - `return_direct_response`: A flag to indicate if the agent should return a direct response.
    - `final_answer`: The final answer to the user's query.

    # --- NEW FIELDS FOR PHASE 1 --- #
    intake: IntakeOutput
    cluster: ClusterOutput
    artisan_clusters: Optional[List[dict[str, Any]]]
    supplier_quotes: Optional[List[dict[str, Any]]]
    final_order: Optional[dict[str, Any]]
    shipping_label_url: Optional[str]
    """
    initial_query: str
    chat_history: List[BaseMessage]
    current_agent_name: str
    tool_code: str
    tool_output: str
    parsed_tool_output: str
    error: str
    return_direct_response: bool
    final_answer: str

    # --- NEW FIELDS FOR PHASE 1 --- #
    intake: IntakeOutput
    cluster: ClusterOutput
    artisan_clusters: Optional[List[dict[str, Any]]]
    supplier_quotes: Optional[List[dict[str, Any]]]
    final_order: Optional[dict[str, Any]]
    shipping_label_url: Optional[str]
